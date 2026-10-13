"""Build the clean alert tables (Task 1 of the pipeline).

Inputs  (data/raw, see scripts/download_data.py and scripts/scrape_telegram.py)
Outputs data/processed/raions.csv           raion universe with English names
        data/processed/alerts_raion.parquet  merged raion-wide air-raid alerts per raion (D58: no hromada/city rows)
        data/processed/alerts_local.parquet  merged hromada/city air-raid alerts (D58), with their raion
        data/processed/alerts_oblast.parquet merged alerts per oblast (+ verified volunteer patches)
        data/processed/masks.parquet         (start, end): raion truth unknown nationwide (source hole)
        data/processed/official_labels.parquet  message type of every official row
        reports/data_quality.md

Usage: PYTHONPATH=. python scripts/build_alert_table.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.alerts.build import WIDE_LEVELS, explained_by, local_events, merge_intervals, oblast_table, raion_events
from src.alerts.sources import (ARCHIVE_COMPLETE_FROM, EXCLUDED_OBLASTS, OFFICIAL_LAST, load_archive, load_official,
                                load_volunteer, raion_universe)
from src.alerts.telegram import label_official, load_channel

RAW, OUT, REP = Path("data/raw"), Path("data/processed"), Path("reports")
HOLE_MIN = pd.Timedelta("2h")  # archive silence this long nationwide is suspicious
ACTIVE_THREAT_POSTS = 10       # ...and a hole if @war_monitor posts at least this many threat messages meanwhile
MAX_ACTIVE_SHARE = 0.5         # ...and fewer than half of the raions are already under alert (D29, user 2026-10-12)
LONG_ALERT = pd.Timedelta("3D")  # data-quality guard (D58): list every alert running longer than this
OFFICIAL_HOLE_MIN = pd.Timedelta("24h")  # official feed silent this long nationwide...
OFFICIAL_HOLE_VOL_PER_H = 2.0            # ...while volunteers log at least this many alerts per hour = an outage (D59)
FIXES = Path("data/fixes/stuck_alerts.csv")  # reviewed corrections of stuck official alerts (D59)
FRONT_OBLASTS = {"Донецька область", "Запорізька область", "Харківська область", "Сумська область", "Чернігівська область",
                 "Дніпропетровська область", "Херсонська область", "Миколаївська область"}
ALWAYS_ON = 0.9                  # ...and every unit under alert for more than this share of a calendar week
QUIRK_OBLASTS = {"Львівська область", "Волинська область", "Херсонська область"}  # D26 finding


def find_holes(archive_air, volunteer, war_monitor, n_raions):
    """Archive silences >= HOLE_MIN with unexplained volunteer alerts, verified by @war_monitor activity."""
    starts = archive_air[archive_air.start >= ARCHIVE_COMPLETE_FROM].start.sort_values()
    gaps = pd.DataFrame({"gap_start": starts.iloc[:-1].reset_index(drop=True),
                         "gap_end": starts.iloc[1:].reset_index(drop=True)})
    gaps = gaps[(gaps.gap_end - gaps.gap_start) >= HOLE_MIN].reset_index(drop=True)
    v = volunteer[(volunteer.start >= ARCHIVE_COMPLETE_FROM) & ~volunteer.oblast.isin(EXCLUDED_OBLASTS | QUIRK_OBLASTS)]
    rows, patches, masks = [], [], []
    for g in gaps.itertuples():
        inside = v[(v.start > g.gap_start) & (v.start < g.gap_end)]
        unexpl = inside[~explained_by(inside, archive_air)] if len(inside) else inside
        wm = war_monitor[war_monitor.published.between(g.gap_start, g.gap_end)]
        threat = wm.text.str.contains("КР|ракет|балістик|БпЛА|реактив|шахед", case=False).sum()
        mid = g.gap_start + (g.gap_end - g.gap_start) / 2
        act = archive_air[(archive_air.start <= mid) & (archive_air.end > mid) & archive_air.raion.notna()
                          & archive_air.loc_level.isin(WIDE_LEVELS)]  # raion-wide alerts only (D58)
        active_share = act[["oblast", "raion"]].drop_duplicates().shape[0] / n_raions
        # a silence is only suspicious if most raions could have started a new alert (were not already under alert)
        hole = threat >= ACTIVE_THREAT_POSTS and active_share < MAX_ACTIVE_SHARE
        patch = hole and len(unexpl) > 0
        rows.append(dict(gap_start=g.gap_start, gap_end=g.gap_end, hours=round((g.gap_end - g.gap_start).total_seconds() / 3600, 2),
                         volunteer_unexplained=len(unexpl), war_monitor_threat_posts=int(threat),
                         raions_already_under_alert=round(active_share, 2),
                         judged_hole=hole, volunteer_patches=len(unexpl) if patch else 0))
        if hole:  # raion truth unknown everywhere in the window; oblast truth patched from volunteer
            masks.append(dict(start=g.gap_start, end=g.gap_end))
        if patch:
            patches.append(unexpl)
    patches = pd.concat(patches, ignore_index=True) if patches else pd.DataFrame(columns=["oblast", "start", "end"])
    return pd.DataFrame(rows), patches, pd.DataFrame(masks, columns=["start", "end"])


def official_holes(official, volunteer):
    """Outages of the official feed (D59): nationwide silences >= OFFICIAL_HOLE_MIN while the volunteer source is busy.
    In the pinned data only 2026-08-29 04:55 -> 2026-09-02 13:48 (105 h, ~7 volunteer alerts per hour) qualifies."""
    s = official.start.sort_values().reset_index(drop=True)
    g = pd.DataFrame({"start": s.iloc[:-1].reset_index(drop=True), "end": s.iloc[1:].reset_index(drop=True)})
    g = g[(g.end - g.start) >= OFFICIAL_HOLE_MIN].reset_index(drop=True)
    vs = volunteer.start.sort_values().reset_index(drop=True)
    vol = vs.searchsorted(g.end) - vs.searchsorted(g.start, side="right")
    hours = (g.end - g.start).dt.total_seconds() / 3600
    return g[(vol / hours) >= OFFICIAL_HOLE_VOL_PER_H].reset_index(drop=True)


def clip_to_holes(labeled, holes):
    """An official alert running into an outage got its end only when the feed came back (days later); its true end is
    unknown. Cut it at the outage start: the outage itself is masked, so no target ever uses the cut part."""
    out = labeled.copy()
    for h in holes.itertuples():
        hit = (out.start < h.start) & (out.end > h.start)
        out.loc[hit, "end"] = h.start
    return out


def apply_fixes(labeled):
    """Stuck official alerts (a lost end message, D59): reviewed rows in data/fixes/stuck_alerts.csv get a new end.
    A row matches on oblast, raion and start (to the second); every fix must match at least one row."""
    fx = pd.read_csv(FIXES, parse_dates=["start_utc", "new_end_utc"])
    out = labeled.copy()
    key = out.start.dt.floor("s")
    for f in fx.itertuples():
        hit = (out.oblast == f.oblast) & (out.raion == f.raion) & (key == f.start_utc)
        assert hit.any(), f"fix matches no row: {f.oblast} / {f.raion} / {f.start_utc}"
        out.loc[hit, "end"] = f.new_end_utc
    return out, fx


def weekly_share(tab, keys):
    """Share of each calendar week (Mon 00:00 UTC) that a unit spends under alert, from merged intervals."""
    rows = []
    for k, g in tab.groupby(keys):
        for r in g.itertuples(index=False):
            s, e = r.start, r.end
            wk = s.floor("D") - pd.Timedelta(days=s.dayofweek)
            while wk < e:
                nxt = wk + pd.Timedelta("7D")
                rows.append((*((k,) if isinstance(k, str) else k), wk, (min(e, nxt) - max(s, wk)).total_seconds()))
                wk = nxt
    d = pd.DataFrame(rows, columns=keys + ["week", "sec"])
    return d.groupby(keys + ["week"]).sec.sum().div(7 * 86400).rename("share").reset_index()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    REP.mkdir(exist_ok=True)
    versions = json.loads(Path("data/versions.json").read_text())
    official = load_official(RAW / "vadimkin/official_data_uk.csv", RAW / "vadimkin/official_data_en.csv")
    archive = load_archive(RAW / "justjimer/alerts_in_ua.csv")
    volunteer = load_volunteer(RAW / "vadimkin/volunteer_data_uk.csv")
    aau = load_channel(str(RAW / "telegram/air_alert_ua/part*.jsonl"))
    wmon = load_channel(str(RAW / "telegram/war_monitor.jsonl"))
    snapshot = archive.start.max().ceil("min")
    universe = raion_universe(official)

    labeled = raw_labels = label_official(official, aau)  # raw_labels: the source as it is, saved below
    off_holes = official_holes(official[official.start < OFFICIAL_LAST], volunteer)
    labeled = clip_to_holes(labeled, off_holes)
    labeled, fixes = apply_fixes(labeled)
    ev, dropped = raion_events(labeled, archive, volunteer, universe, snapshot)
    raion = merge_intervals(ev, ["oblast", "raion"])
    local = local_events(labeled, archive, universe, snapshot)
    air = archive[archive.alert_type == "air_raid"].assign(end=lambda d: d.end.fillna(snapshot))
    holes, patches, masks = find_holes(air, volunteer, wmon, len(universe))
    # official-feed outages (D59): raion truth unknown -> masks; oblast truth from volunteer alerts (as D26)
    vq = volunteer[~volunteer.oblast.isin(EXCLUDED_OBLASTS | QUIRK_OBLASTS)]
    off_patch = [vq[(vq.start >= h.start) & (vq.start < h.end)] for h in off_holes.itertuples()]
    patches = pd.concat([patches, *off_patch], ignore_index=True) if off_patch else patches
    masks = pd.concat([masks, off_holes[["start", "end"]]], ignore_index=True)
    obl = oblast_table(raion, patches)

    universe.to_csv(OUT / "raions.csv", index=False)
    raion.to_parquet(OUT / "alerts_raion.parquet")
    local.to_parquet(OUT / "alerts_local.parquet")
    obl.to_parquet(OUT / "alerts_oblast.parquet")
    masks.to_parquet(OUT / "masks.parquet")
    raw_labels[["row_id", "oblast", "raion", "hromada", "loc_level", "start", "end", "kind", "label_how"]].to_parquet(OUT / "official_labels.parquet")

    # ---- report ----
    L = []
    w = L.append
    w("# Data quality report\n")
    w(f"Built {pd.Timestamp.now(tz='UTC'):%Y-%m-%d %H:%M} UTC from Vadimkin `{versions['vadimkin']['commit'][:8]}`, "
      f"JustJimer `{versions['justjimer']['commit'][:8]}`, @air_alert_ua posts #{aau.id.min()}–#{aau.id.max()} "
      f"({len(aau):,} posts), @war_monitor {len(wmon):,} posts.\n")
    w("## 1. Official rows by message type (D25)\n")
    w("Each row of the official dataset was traced back to the @air_alert_ua message that created it "
      "(same timestamp; location from the message hashtags). Only `air_raid` rows are used, plus `unknown` "
      "rows at oblast/raion level (artillery and other threats only ever appear at hromada level).\n")
    t = pd.crosstab(labeled.kind, labeled.loc_level, margins=True)
    w("```\n" + t.to_string() + "\n```\n")
    w("How the rows were matched:\n\n```\n" + labeled.label_how.value_counts().to_string() + "\n```\n")
    w("## 2. Raion alert table\n")
    w(f"- Raions: {universe.raion.nunique()} in {universe.oblast.nunique()} oblasts (incl. Kyiv City; Luhansk and Crimea excluded).")
    w(f"- Raw raion events (after disaggregation): {len(ev):,}; events whose raion is unknown (dropped): {len(dropped):,}.")
    w(f"- Merged raion alerts: {len(raion):,}, from {raion.start.min():%Y-%m-%d} to {raion.start.max():%Y-%m-%d %H:%M} UTC.")
    w(f"- Merged oblast alerts: {len(obl):,}.\n")
    w("Sources of merged raion alerts:\n\n```\n" + raion.sources.value_counts().to_string() + "\n```\n")
    yr = raion.assign(year=raion.start.dt.year).groupby("year").agg(alerts=("start", "size"), median_min=("duration_min", "median"))
    w("Per year:\n\n```\n" + yr.round(1).to_string() + "\n```\n")
    if len(dropped):
        w("Dropped events by place (unknown raion):\n\n```\n" + dropped.assign(p=dropped.oblast.astype(str) + " / " + dropped.raion.astype(str))
          .p.value_counts().head(10).to_string() + "\n```\n")
    w("## 2b. Local (hromada/city) alerts, kept apart from raion alerts (D58)\n")
    w(f"- Merged local alerts: {len(local):,} in {local.hromada.nunique()} hromadas/cities; they are model inputs and site notes, "
      "never the raion's own alert.\n")
    w("## 2c. Guards: very long alerts and units that are almost always under alert (D58)\n")
    for name, tab, keys in (("raion", raion, ["oblast", "raion"]), ("oblast", obl, ["oblast"]), ("local", local, ["oblast", "raion", "hromada"])):
        lo = tab[(tab.end - tab.start) > LONG_ALERT]
        w(f"{name.title()} alerts longer than {LONG_ALERT.days} days: {len(lo)}")
        if len(lo):
            w("```\n" + lo.assign(days=((lo.end - lo.start).dt.total_seconds() / 86400).round(1))
              .sort_values("days", ascending=False)[keys + ["start", "end", "days"]].head(15).to_string(index=False) + "\n```")
    odd = raion[(raion.duration_min > 24 * 60) & ~raion.oblast.isin(FRONT_OBLASTS)]
    w(f"\nRaion alerts longer than 24 h outside the front-line/border oblasts (review these; a lost end message is fixed "
      f"in `{FIXES}`): {len(odd)}")
    if len(odd):
        w("```\n" + odd.assign(hours=(odd.duration_min / 60).round(1))[["oblast", "raion", "start", "end", "sources", "hours"]]
          .to_string(index=False) + "\n```")
    w(f"\nApplied corrections from `{FIXES}`: {len(fixes)}")
    w("```\n" + fixes[["oblast", "raion", "start_utc", "new_end_utc"]].to_string(index=False) + "\n```")
    for name, tab, keys in (("raion", raion, ["oblast", "raion"]), ("oblast", obl, ["oblast"])):
        wk = weekly_share(tab, keys)
        bad = wk[wk.share > ALWAYS_ON]
        w(f"\n{name.title()}-weeks under alert more than {ALWAYS_ON:.0%} of the time: {len(bad)}"
          + (" (expected only for front-line raions of Donetsk/Kharkiv/Sumy/Zaporizhzhia/Kherson oblasts; a raion "
             "outside them here means a data problem)" if len(bad) else ""))
        if len(bad):
            w("```\n" + bad.groupby(keys).size().rename("weeks").sort_values(ascending=False).head(20).to_string() + "\n```")
    w("")
    w("## 3. Yellow/red (reform period, archive)\n")
    rr = raion[raion.red.notna() & (raion.start >= ARCHIVE_COMPLETE_FROM)]
    w(f"- Raion alerts with a level: {len(rr):,}; share red: {rr.red.astype(float).mean():.2f}.\n")
    w("## 4. Holes in the archive and volunteer patches (D26)\n")
    w(f"Archive silences of at least {HOLE_MIN.total_seconds() / 3600:.0f} hours nationwide, checked against volunteer alerts and @war_monitor:\n")
    w("```\n" + (holes.to_string(index=False) if len(holes) else "none") + "\n```\n")
    w(f"Volunteer alerts used as oblast-level patches: {len(patches)}"
      + (f" ({', '.join(sorted(patches.oblast.unique()))})" if len(patches) else "") + ".")
    w("A silence counts as a hole when @war_monitor shows heavy threat activity at the same time (at least "
      f"{ACTIVE_THREAT_POSTS} threat posts) **and** fewer than {MAX_ACTIVE_SHARE:.0%} of the raions are already under "
      "alert (if most of the country is already under alert, no new alert can start, so silence is normal; "
      "e.g. 2026-10-07, confirmed by the user's alerts.in.ua screenshot). Raion truth "
      "is then unknown nationwide, so the window is written to `masks.parquet` and excluded from raion targets.\n")
    w("## 4b. Outages of the official feed (D59)\n")
    w(f"Nationwide silences of the official feed of at least {OFFICIAL_HOLE_MIN.total_seconds() / 3600:.0f} h while the "
      f"volunteer source logs at least {OFFICIAL_HOLE_VOL_PER_H:g} alerts per hour. Raion truth is masked there; official "
      "alerts running into the outage are cut at its start (their recorded end is when the feed came back); the oblast "
      f"table uses the volunteer alerts of the outage (outside the quirk oblasts): {sum(len(x) for x in off_patch)} alerts.\n")
    w("```\n" + (off_holes.assign(hours=((off_holes.end - off_holes.start).dt.total_seconds() / 3600).round(1)).to_string(index=False)
                  if len(off_holes) else "none") + "\n```\n")
    w("## 5. Volunteer quirk in Lviv, Volyn, Kherson (D26)\n")
    w("The volunteer source reports far more alerts in these oblasts than the official system, both before the "
      "reform (vs the official dataset) and after it (vs the archive), and @war_monitor never mentions those "
      "oblasts around the unexplained alerts. These volunteer alerts are therefore **not** used as patches.\n")
    (REP / "data_quality.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()

"""Build the clean alert tables (Task 1 of the pipeline).

Inputs  (data/raw, see scripts/download_data.py and scripts/scrape_telegram.py)
Outputs data/processed/raions.csv           raion universe with English names
        data/processed/alerts_raion.parquet  merged air-raid alerts per raion
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

from src.alerts.build import explained_by, merge_intervals, oblast_table, raion_events
from src.alerts.sources import (ARCHIVE_COMPLETE_FROM, EXCLUDED_OBLASTS, load_archive, load_official,
                                load_volunteer, raion_universe)
from src.alerts.telegram import label_official, load_channel

RAW, OUT, REP = Path("data/raw"), Path("data/processed"), Path("reports")
HOLE_MIN = pd.Timedelta("2h")  # archive silence this long nationwide is suspicious
ACTIVE_THREAT_POSTS = 10       # ...and a hole if @war_monitor posts at least this many threat messages meanwhile
MAX_ACTIVE_SHARE = 0.5         # ...and fewer than half of the raions are already under alert (D29, user 2026-10-12)
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
        act = archive_air[(archive_air.start <= mid) & (archive_air.end > mid) & archive_air.raion.notna()]
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

    labeled = label_official(official, aau)
    ev, dropped = raion_events(labeled, archive, volunteer, universe, snapshot)
    raion = merge_intervals(ev, ["oblast", "raion"])
    air = archive[archive.alert_type == "air_raid"].assign(end=lambda d: d.end.fillna(snapshot))
    holes, patches, masks = find_holes(air, volunteer, wmon, len(universe))
    obl = oblast_table(raion, patches)

    universe.to_csv(OUT / "raions.csv", index=False)
    raion.to_parquet(OUT / "alerts_raion.parquet")
    obl.to_parquet(OUT / "alerts_oblast.parquet")
    masks.to_parquet(OUT / "masks.parquet")
    labeled[["row_id", "oblast", "raion", "hromada", "loc_level", "start", "end", "kind", "label_how"]].to_parquet(OUT / "official_labels.parquet")

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
    w("## 5. Volunteer quirk in Lviv, Volyn, Kherson (D26)\n")
    w("The volunteer source reports far more alerts in these oblasts than the official system, both before the "
      "reform (vs the official dataset) and after it (vs the archive), and @war_monitor never mentions those "
      "oblasts around the unexplained alerts. These volunteer alerts are therefore **not** used as patches.\n")
    (REP / "data_quality.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()

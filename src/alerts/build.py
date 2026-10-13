"""Combine sources into clean alert tables (decisions.md D2, D19, D22, D25–D27).

Raion table: one row per (merged) alert in a raion.
  - official dataset, air raids only (labelled via @air_alert_ua messages, D25)
  - alerts.in.ua archive (air_raid only), which carries yellow/red from 2026-09-06
  - volunteer data only before the official feed starts (2022-02-24 .. 2022-03-15, oblast-wide era)
  An oblast-wide alert counts for every raion of the oblast ("disaggregation", D22).
  A hromada/city alert does NOT count for its raion (D58, replaces D27): a few front-line hromadas are under one alert
  for months (Lyptsi, Kharkivskyi raion, from 2024-05 for ~14,500 h), which made whole raions look permanently alerted.
Local table: hromada/city air-raid alerts, kept with the hromada name and its raion (D58); used as model inputs and
  shown on the site as notes, never as the raion's own alert.
Oblast table: union of the oblast's raion alerts (+ verified volunteer patches, D26).
Masks: periods where a source hole makes raion truth unknown (excluded from training/scoring targets).
"""
import numpy as np
import pandas as pd

from .sources import EXCLUDED_OBLASTS, KYIV_CITY, OFFICIAL_LAST

OFFICIAL_FIRST = pd.Timestamp("2022-03-15", tz="UTC")


def expand_to_raions(ev, universe):
    """Turn location-level events into raion events. ev needs oblast, raion, loc_level."""
    ev = ev[~ev.oblast.isin(EXCLUDED_OBLASTS)]
    raions = universe.groupby("oblast").raion.apply(list).to_dict()
    whole = ev[ev.loc_level == "oblast"].copy()
    whole["raion"] = whole.oblast.map(raions)
    whole = whole.explode("raion")
    part = ev[ev.loc_level != "oblast"]
    out = pd.concat([whole, part], ignore_index=True)
    known = set(zip(universe.oblast, universe.raion))
    ok = pd.Series([k in known for k in zip(out.oblast, out.raion)], index=out.index)
    return out[ok], out[~ok]


def merge_intervals(ev, keys):
    """Union of overlapping alerts per unit. Keeps red = any part red, and the set of sources."""
    ev = ev.sort_values(keys + ["start"])
    out = []
    for k, g in ev.groupby(keys, sort=False):
        cur = None
        for r in g.itertuples(index=False):
            if cur is not None and r.start <= cur["end"]:
                cur["end"] = max(cur["end"], r.end)
                cur["n_parts"] += 1
                cur["sources"].add(r.source)
                if pd.notna(r.red):
                    cur["red"] = bool(r.red) or (pd.notna(cur["red"]) and bool(cur["red"]))
            else:
                if cur is not None:
                    out.append(cur)
                cur = dict(zip(keys, k if isinstance(k, tuple) else (k,)), start=r.start, end=r.end,
                           red=r.red, n_parts=1, sources={r.source})
        out.append(cur)
    m = pd.DataFrame(out)
    m["sources"] = m.sources.map(lambda s: "+".join(sorted(s)))
    m["duration_min"] = (m.end - m.start).dt.total_seconds() / 60
    return m


WIDE_LEVELS = ("oblast", "raion")  # declared for the whole raion or the whole oblast (D58)


def raion_events(official_labeled, archive, volunteer, universe, snapshot_time):
    """Raion-wide air-raid events (declared for the raion or its oblast), before merging. Hromada/city rows are
    left out here (D58); see local_events."""
    o = official_labeled[official_labeled.kind.isin(["air_raid", "unknown"]) & official_labeled.loc_level.isin(WIDE_LEVELS)]
    o = o.assign(source="official", red=np.nan)[["oblast", "raion", "loc_level", "start", "end", "source", "red"]]
    a = archive[(archive.alert_type == "air_raid") & archive.loc_level.isin(WIDE_LEVELS)].copy()
    a["end"] = a.end.fillna(snapshot_time)  # still active when the archive was saved
    a = a.assign(source="archive")[["oblast", "raion", "loc_level", "start", "end", "source", "red"]]
    v = volunteer[(volunteer.start < OFFICIAL_FIRST)].assign(loc_level="oblast", raion=pd.NA, source="volunteer", red=np.nan)
    v = v[["oblast", "raion", "loc_level", "start", "end", "source", "red"]]
    ev = pd.concat([o, a, v], ignore_index=True)
    ev = ev[ev.end > ev.start]
    return expand_to_raions(ev, universe)


def local_events(official_labeled, archive, universe, snapshot_time):
    """Hromada/city air-raid alerts (D58), merged per (oblast, raion, hromada). Official `unknown` rows at hromada level
    stay out (mostly artillery threats, D27). An archive city record duplicates its hromada record (same start); the city
    copy is dropped when the hromada copy exists."""
    o = official_labeled[(official_labeled.kind == "air_raid") & (official_labeled.loc_level == "hromada")]
    o = o.assign(source="official", red=np.nan)[["oblast", "raion", "hromada", "start", "end", "source", "red"]]
    a = archive[(archive.alert_type == "air_raid") & (archive.loc_level == "hromada")].copy()
    a["end"] = a.end.fillna(snapshot_time)
    is_city = a.location_type == "city"
    twin = a[~is_city].assign(k=lambda d: d.raion.astype(str) + "|" + d.start.dt.floor("s").astype(str)).k
    key = a.raion.astype(str) + "|" + a.start.dt.floor("s").astype(str)
    a = a[~(is_city & key.isin(set(twin)))]
    a = a.assign(source="archive")[["oblast", "raion", "hromada", "start", "end", "source", "red"]]
    ev = pd.concat([o, a], ignore_index=True)
    ev = ev[(ev.end > ev.start) & ~ev.oblast.isin(EXCLUDED_OBLASTS)]
    known = set(zip(universe.oblast, universe.raion))
    ev = ev[[k in known for k in zip(ev.oblast, ev.raion)]]
    return merge_intervals(ev, ["oblast", "raion", "hromada"])


def oblast_table(raion_merged, patches=None):
    ev = raion_merged[["oblast", "start", "end", "red"]].assign(source=raion_merged.sources)
    if patches is not None and len(patches):
        ev = pd.concat([ev, patches.assign(source="volunteer_patch", red=np.nan)[["oblast", "start", "end", "red", "source"]]])
    return merge_intervals(ev, ["oblast"])


def explained_by(volunteer, archive_raion, tol=pd.Timedelta("10min")):
    """For each volunteer alert: is there an archive alert in the same oblast active at its start
    or starting within ±tol? (D19 follow-up)."""
    by_ob = {k: g for k, g in archive_raion.groupby("oblast")}
    res = []
    for r in volunteer.itertuples():
        g = by_ob.get(r.oblast)
        if g is None:
            res.append(False)
            continue
        near = ((g.start - r.start).abs() <= tol).any()
        active = ((g.start <= r.start) & (g.end > r.start)).any()
        res.append(bool(near or active))
    return pd.Series(res, index=volunteer.index)


__all__ = ["expand_to_raions", "merge_intervals", "raion_events", "local_events", "oblast_table", "explained_by",
           "OFFICIAL_LAST", "KYIV_CITY"]

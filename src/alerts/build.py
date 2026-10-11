"""Combine sources into clean alert tables (decisions.md D2, D19, D22, D25–D27).

Raion table: one row per (merged) alert in a raion.
  - official dataset, air raids only (labelled via @air_alert_ua messages, D25)
  - alerts.in.ua archive (air_raid only), which carries yellow/red from 2026-09-06
  - volunteer data only before the official feed starts (2022-02-24 .. 2022-03-15, oblast-wide era)
  An oblast-wide alert counts for every raion of the oblast ("disaggregation", D22); a hromada/city alert
  counts for its raion (the raion is "under alert somewhere", D27).
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


def raion_events(official_labeled, archive, volunteer, universe, snapshot_time):
    """All air-raid events at raion level, before merging."""
    o = official_labeled[official_labeled.kind.isin(["air_raid", "unknown"]) &
                         ~((official_labeled.kind == "unknown") & (official_labeled.loc_level == "hromada"))]
    o = o.assign(source="official", red=np.nan)[["oblast", "raion", "loc_level", "start", "end", "source", "red"]]
    a = archive[archive.alert_type == "air_raid"].copy()
    a["end"] = a.end.fillna(snapshot_time)  # still active when the archive was saved
    a = a.assign(source="archive")[["oblast", "raion", "loc_level", "start", "end", "source", "red"]]
    v = volunteer[(volunteer.start < OFFICIAL_FIRST)].assign(loc_level="oblast", raion=pd.NA, source="volunteer", red=np.nan)
    v = v[["oblast", "raion", "loc_level", "start", "end", "source", "red"]]
    ev = pd.concat([o, a, v], ignore_index=True)
    ev = ev[ev.end > ev.start]
    return expand_to_raions(ev, universe)


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


__all__ = ["expand_to_raions", "merge_intervals", "raion_events", "oblast_table", "explained_by",
           "OFFICIAL_LAST", "KYIV_CITY"]

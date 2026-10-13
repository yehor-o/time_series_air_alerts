"""Hourly forecasting table: features (known before t) and targets (after t), per unit.

Issue times t are whole UTC hours. For a unit (raion or oblast) with merged, non-overlapping alerts
(starts s_i, ends e_i), everything below is computed from these intervals only:

  features (past, leakage-safe):
    - only alerts with s_i < t are used;
    - an alert active at t (s_i < t < e_i) is used as "active since s_i"; its end e_i is never used;
    - ended alerts (e_i <= t) are used with their end.
  targets (future): new starts in [t, t+h), alert time in [t, t+24h), the duration of the next alert.

Optional inputs, same rules:
  local alerts (D58): hromada/city alerts inside the unit, per hromada; never part of the unit's own alert or targets.
  neighbours (D55): the units that share a border, computed from their own (raion-wide) alerts.

tests/test_leakage.py checks the rule mechanically: features at t computed from data truncated at t
(alerts starting after t deleted, ends after t hidden) must equal features from the full data.
"""
import numpy as np
import pandas as pd

H = np.timedelta64(1, "h")
CAP_H = 24 * 30  # "hours since" features are capped at 30 days
UNKNOWN_END = np.datetime64("2100-01-01T00:00:00", "ns")


def as_ns(x):
    return np.asarray(pd.DatetimeIndex(x).tz_convert(None) if getattr(x, "tz", None) is not None
                      else pd.DatetimeIndex(x), dtype="datetime64[ns]")


def covered_until(x, s, e):
    """Total alert time (hours) in (-inf, x) for sorted non-overlapping intervals; x is an array of times."""
    dur = (e - s) / H
    cum = np.concatenate([[0.0], np.cumsum(dur)])
    i = np.searchsorted(s, x, side="left")           # intervals started before x
    j = np.searchsorted(e, x, side="right")          # intervals ended at or before x
    partial = np.where(i > j, (x - s[np.maximum(i - 1, 0)]) / H, 0.0)  # the one still running at x
    return cum[j] + partial


def unit_series(s, e, grid):
    """Per-hour arrays for one unit. grid = issue times (datetime64[ns]); s, e sorted datetime64[ns].
    e may contain UNKNOWN_END for alerts whose end is not known yet."""
    edges = np.append(grid, grid[-1] + H)
    n_start = np.histogram(s.view("int64"), bins=edges.view("int64"))[0].astype(np.int32)
    i = np.searchsorted(s, grid, side="left")
    prev = np.maximum(i - 1, 0)
    has_prev = i > 0
    active = has_prev & (e[prev] > grid)
    h_since_start = np.where(has_prev, (grid - s[prev]) / H, CAP_H)
    j = np.searchsorted(e, grid, side="right")
    h_since_end = np.where(active, 0.0, np.where(j > 0, (grid - e[np.maximum(j - 1, 0)]) / H, CAP_H))
    # median duration (minutes) of the last 10 alerts that already ended
    # (alerts ended so far = the first j by end time; intervals don't overlap, so same order as starts)
    durs = (e - s) / np.timedelta64(1, "m")
    meds = np.array([np.nan] + [np.median(durs[max(n - 10, 0):n]) for n in range(1, len(s) + 1)])
    med_dur = meds[j]
    return {
        "n_start": n_start,
        "active": active.astype(np.float32),
        "h_since_start": np.minimum(h_since_start, CAP_H),
        "h_since_end": np.minimum(h_since_end, CAP_H),
        "cov": covered_until(grid, s, e),  # cumulative alert hours up to each t (past only)
        "med_dur10": med_dur,
    }


def local_series(hromadas, grid):
    """Inputs from the local (hromada/city) alerts of one unit; hromadas = list of (s, e) per hromada (sorted, merged).
    Same rules as unit_series: starts before t, an alert running at t is known only as running."""
    edges = np.append(grid, grid[-1] + H).view("int64")
    n_start = np.zeros(len(grid), np.int32)
    n_active = np.zeros(len(grid), np.float32)
    n_new = np.zeros(len(grid), np.float32)
    for s, e in hromadas:
        n_start += np.histogram(s.view("int64"), bins=edges)[0].astype(np.int32)
        i = np.searchsorted(s, grid, side="left")
        prev = np.maximum(i - 1, 0)
        act = (i > 0) & (e[prev] > grid)
        n_active += act
        n_new += act & ((grid - s[prev]) < 24 * H)
    return n_start, n_active, n_new


def past_sum(x, w):
    """Sum of x over the w hourly bins strictly before t."""
    c = np.concatenate([[0], np.cumsum(x)])
    k = np.arange(len(x))
    return c[k] - c[np.maximum(k - w, 0)]


def same_hour_rate(any_start, days):
    """Share of the last `days` days with a start in the same (UTC) hour, strictly before t."""
    out = np.zeros(len(any_start))
    for d in range(1, days + 1):
        out[24 * d:] += any_start[:-24 * d]
    return out / days


def period_rate(any_start, grid_local_hour, grid_local_date, night=True, days=14):
    """Share of the last `days` completed nights (22:00-06:00 Kyiv) or days (06:00-22:00) with >= 1 start."""
    h = grid_local_hour
    in_period = ((h >= 22) | (h < 6)) if night else ((h >= 6) & (h < 22))
    # label each period: nights by the date they end on, days by their date
    label = grid_local_date + np.where(night & (h >= 22), np.timedelta64(1, "D"), np.timedelta64(0, "D"))
    df = pd.DataFrame({"label": label, "hit": any_start & in_period, "in": in_period})
    per = df[df["in"]].groupby("label").hit.max().astype(float)
    # a period counts once it has finished: nights at 06:00 of `label`, days at 22:00 of `label`
    end_hour = 6 if night else 22
    finished_at = per.index.values + np.timedelta64(end_hour, "h")
    roll = per.rolling(days, min_periods=1).mean().values
    now_local = grid_local_date + h.astype("timedelta64[h]")
    idx = np.searchsorted(finished_at, now_local, side="right") - 1
    return np.where(idx >= 0, roll[np.maximum(idx, 0)], np.nan)


def targets(n_start, cov, grid, s, e, last_known):
    """Future targets for one unit; NaN where the window runs past the last known time."""
    any_start = n_start > 0
    k = np.arange(len(grid))
    c = np.concatenate([[0], np.cumsum(any_start)])
    cn = np.concatenate([[0], np.cumsum(n_start)])
    n = len(grid)

    def window(h, cum):
        return cum[np.minimum(k + h, n)] - cum[k]

    out = {}
    for h in (1, 3):
        out[f"y_start_{h}h"] = (window(h, c) > 0).astype(float)
    out["y_count_24h"] = window(24, cn).astype(float)
    cov_next = covered_until(grid + 24 * H, s, e) - cov
    out["y_hours_24h"] = cov_next
    for b in range(4):  # timing: a start in hours [6b, 6b+6) after t
        out[f"y_block{b}_24h"] = ((c[np.minimum(k + 6 * b + 6, n)] - c[np.minimum(k + 6 * b, n)]) > 0).astype(float)
    # duration (minutes) of the first alert starting in [t, t+3h); NaN if none or still running
    nxt = np.searchsorted(s, grid, side="left")
    has = (nxt < len(s))
    st = np.where(has, s[np.minimum(nxt, len(s) - 1)], np.datetime64("NaT", "ns"))
    en = np.where(has, e[np.minimum(nxt, len(s) - 1)], np.datetime64("NaT", "ns"))
    dur = (en - st) / np.timedelta64(1, "m")
    for h in (1, 3):
        ok = has & (st < grid + h * H) & (en <= last_known)
        out[f"y_dur_{h}h"] = np.where(ok, dur, np.nan)
    horizon = {"y_start_1h": 1, "y_start_3h": 3, "y_count_24h": 24, "y_hours_24h": 24,
               **{f"y_block{b}_24h": 24 for b in range(4)}}
    for name, h in horizon.items():
        out[name] = np.where(grid + h * H <= last_known, out[name], np.nan)
    return out


def build_panel(intervals, units, grid, last_known, parent=None, masks=None, local=None, neighbours=None):
    """Feature + target table.

    intervals: DataFrame with unit columns, start, end (merged per unit).
    units: list of unit keys (tuples of the unit columns' values).
    parent: optional dict unit -> parent key (raion -> oblast) for context features.
    masks: DataFrame(start, end) of periods with unknown truth; targets overlapping them become NaN.
    local: optional DataFrame with the unit columns, hromada, start, end (D58) -> local_* inputs.
    neighbours: optional dict unit -> list of units sharing a border (D55) -> nb_* inputs.
    """
    cols = intervals.attrs.get("unit_cols", ["unit"])
    g = as_ns(grid)
    kyiv = pd.DatetimeIndex(grid).tz_convert("Europe/Kyiv")
    lhour = kyiv.hour.values
    ldate = np.asarray(kyiv.tz_localize(None).normalize(), dtype="datetime64[ns]")
    by_unit = {(k if len(cols) > 1 else k[0]): v for k, v in intervals.groupby(cols)}
    series, frames = {}, []
    for u in units:
        d = by_unit.get(u)
        if d is None:
            s = e = np.array([], dtype="datetime64[ns]")
        else:
            d = d.sort_values("start")
            s, e = as_ns(d.start), as_ns(d.end)
        series[u] = (s, e, unit_series(s, e, g))
    nat_active = np.mean([a["active"] for _, _, a in series.values()], axis=0)
    nat_starts = np.sum([a["n_start"] for _, _, a in series.values()], axis=0)
    par_active, par_starts = {}, {}
    if parent:
        for p in set(parent.values()):
            kids = [u for u in units if parent[u] == p]
            par_active[p] = np.mean([series[u][2]["active"] for u in kids], axis=0)
            par_starts[p] = np.sum([series[u][2]["n_start"] for u in kids], axis=0)
    loc = {}
    if local is not None:
        lk = {(k if len(cols) > 1 else k[0]): v for k, v in local.groupby(cols)}
        for u in units:
            d = lk.get(u)
            hs = [] if d is None else [(as_ns(h.sort_values("start").start), as_ns(h.sort_values("start").end))
                                         for _, h in d.groupby("hromada")]
            loc[u] = local_series(hs, g)
    for u in units:
        s, e, a = series[u]
        any_start = a["n_start"] > 0
        f = {
            "time": grid, "unit": "|".join(u) if isinstance(u, tuple) else u,
            "active": a["active"], "h_since_start": a["h_since_start"], "h_since_end": a["h_since_end"],
            "med_dur10": a["med_dur10"],
            **{f"starts_{w}h": past_sum(a["n_start"], w) for w in (1, 3, 6, 24, 168)},
            **{f"alert_h_{w}h": a["cov"] - covered_until(g - w * H, s, e) for w in (3, 24, 168)},
            "hod_rate7": same_hour_rate(any_start, 7), "hod_rate14": same_hour_rate(any_start, 14),
            "night_rate14": period_rate(any_start, lhour, ldate, night=True),
            "day_rate14": period_rate(any_start, lhour, ldate, night=False),
            "nat_active_share": nat_active,
            **{f"nat_starts_{w}h": past_sum(nat_starts, w) for w in (1, 3, 24)},
            "hour": lhour, "dow": kyiv.dayofweek.values,
        }
        if parent:
            p = parent[u]
            f.update({"parent_active_share": par_active[p],
                      **{f"parent_starts_{w}h": past_sum(par_starts[p], w) for w in (1, 3, 24)}})
        if local is not None:
            ls, la, ln = loc[u]
            f.update({"local_active_n": la, "local_new_active_n": ln,
                      **{f"local_starts_{w}h": past_sum(ls, w) for w in (1, 3, 24)}})
        if neighbours is not None:
            nb = [v for v in neighbours.get(u, []) if v in series]
            act = np.array([series[v][2]["active"] for v in nb]) if nb else np.full((1, len(g)), np.nan)
            st = np.array([series[v][2]["n_start"] for v in nb]) if nb else np.zeros((1, len(g)))
            f.update({"nb_active_share": act.mean(0),
                      **{f"nb_starts_{w}h": past_sum(st.sum(0), w) for w in (1, 3, 24)},
                      "nb_max_starts_24h": np.max([past_sum(x, 24) for x in st], axis=0)})
            if parent:
                other = [v for v in nb if parent[v] != parent[u]]
                f["nb_other_oblast_active_share"] = (np.mean([series[v][2]["active"] for v in other], axis=0)
                                                     if other else np.full(len(g), np.nan))
        f.update(targets(a["n_start"], a["cov"], g, s, e, as_ns(pd.DatetimeIndex([last_known]))[0]))
        frames.append(pd.DataFrame(f))
    panel = pd.concat(frames, ignore_index=True)
    if masks is not None and len(masks):
        t = panel.time
        for m in masks.itertuples():
            for col, h in [("y_start_1h", 1), ("y_start_3h", 3), ("y_dur_1h", 3), ("y_dur_3h", 3),
                           ("y_count_24h", 24), ("y_hours_24h", 24), *[(f"y_block{b}_24h", 24) for b in range(4)]]:
                hit = (t < m.end) & (t + pd.Timedelta(hours=h) > m.start)
                panel.loc[hit, col] = np.nan
    return panel


def truncate(intervals, t):
    """What was known at time t: alerts that started before t; ends after t are unknown."""
    d = intervals[intervals.start < t].copy()
    d["end"] = d.end.where(d.end <= t, pd.Timestamp(UNKNOWN_END, tz="UTC"))
    return d

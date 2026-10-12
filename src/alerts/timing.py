"""Timing model rows (decisions.md D42): "will a new alert start in this 3-hour Kyiv-time block?"
for each of the 56 blocks of the next 7 days.

Blocks are fixed Kyiv clock blocks 00-03, 03-06, ..., 21-24 (8 per local day, built per day so DST
changes keep the clock alignment). A forecast is issued at time t (here 00:00 and 12:00 Kyiv); its
first block is the first block starting at or after t.

Per (unit, issue time, lead b) row:
  inputs  - the unit's hourly features at t (from the panel: alerts now, recent activity, habits, ...)
          - lead_h: hours from t to the block start; block_slot (0..7 = 00:00..21:00 Kyiv); block_dow
          - blk_rate14: share of the last 14 FINISHED same-clock blocks with a new alert (this unit)
          - blk_dow4: same, last 4 finished blocks of the same weekday and clock block
          - parent_blk_rate14 / nat_blk_rate14: blk_rate14 of the oblast / the whole country
  target  - y_block: a new alert starts in the block (NaN if the block ends after the last known time)
Only blocks that ENDED at or before t enter the rate inputs (no look-ahead; see tests/test_leakage.py).
"""
import numpy as np
import pandas as pd

KYIV = "Europe/Kyiv"
N_LEAD = 56


def block_starts(t_from, t_to):
    """UTC start times of all Kyiv clock blocks for local days covering [t_from, t_to], 8 per day."""
    days = pd.date_range(t_from.tz_convert(KYIV).normalize().tz_localize(None) - pd.Timedelta("1D"),
                         t_to.tz_convert(KYIV).normalize().tz_localize(None) + pd.Timedelta("9D"), freq="D")
    loc = [d + pd.Timedelta(hours=3 * s) for d in days for s in range(8)]
    return pd.DatetimeIndex(loc).tz_localize(KYIV, ambiguous=False, nonexistent="shift_forward").tz_convert("UTC")


def issue_times(t_from, t_to, hours=(0, 12)):
    days = pd.date_range(t_from.tz_convert(KYIV).normalize().tz_localize(None),
                         t_to.tz_convert(KYIV).normalize().tz_localize(None), freq="D")
    loc = [d + pd.Timedelta(hours=h) for d in days for h in hours]
    t = pd.DatetimeIndex(loc).tz_localize(KYIV, ambiguous=False, nonexistent="shift_forward").tz_convert("UTC")
    return t[(t >= t_from) & (t <= t_to)]


def block_indicator(hour_times, hour_any, bstarts):
    """Any start per block (1/0), NaN if any hour of the block is unknown (NaN) or outside the data."""
    k = np.searchsorted(bstarts.values, hour_times.values, side="right") - 1
    nb = len(bstarts)
    ok = (k >= 0) & (k < nb)
    hits = np.bincount(k[ok], weights=np.nan_to_num(hour_any[ok]), minlength=nb)
    hours = np.bincount(k[ok], minlength=nb)
    unknown = np.bincount(k[ok], weights=np.isnan(hour_any[ok]).astype(float), minlength=nb)
    expected = np.diff(np.append(bstarts.values, bstarts.values[-1] + np.timedelta64(3, "h"))) / np.timedelta64(1, "h")
    out = (hits > 0).astype(float)
    out[(unknown > 0) | (hours < expected)] = np.nan
    return out


def rate_features(bi, bstarts, issues, lead_idx):
    """blk_rate14 and blk_dow4 for target blocks lead_idx (issues x 56), using blocks ended <= issue time."""
    days = len(bi) // 8
    grid = np.nan_to_num(bi[: days * 8]).reshape(days, 8)
    known = (~np.isnan(bi[: days * 8])).reshape(days, 8).astype(float)
    cs = np.vstack([np.zeros((1, 8)), np.cumsum(grid, 0)])
    ck = np.vstack([np.zeros((1, 8)), np.cumsum(known, 0)])
    ends = np.append(bstarts.values[1:], bstarts.values[-1] + np.timedelta64(3, "h"))
    f = np.searchsorted(ends, issues.values, side="right") - 1  # last block that ended <= t
    slot = lead_idx % 8
    tday = lead_idx // 8
    d_last = (f[:, None] - slot) // 8  # last finished day for this slot
    lo = np.clip(d_last - 13, 0, days)
    hi = np.clip(d_last + 1, 0, days)
    num = cs[hi, slot] - cs[lo, slot]
    den = ck[hi, slot] - ck[lo, slot]
    rate14 = np.where(den > 0, num / np.maximum(den, 1), np.nan)
    m = np.ceil((tday - d_last) / 7).astype(int)
    vals, cnt = np.zeros(lead_idx.shape), np.zeros(lead_idx.shape)
    for r in range(4):
        d = tday - 7 * (m + r)
        okd = d >= 0
        dd = np.clip(d, 0, days - 1)
        v = np.where(okd, bi[dd * 8 + slot], np.nan)
        vals += np.nan_to_num(v)
        cnt += ~np.isnan(v)
    dow4 = np.where(cnt > 0, vals / np.maximum(cnt, 1), np.nan)
    return rate14, dow4


def timing_rows(panel, feats, issues, last_known, parent_of=None):
    """Long table: one row per (unit, issue time, lead block). panel: hourly table with unit, time,
    feats and y_start_1h (the hourly 'new alert starts' indicator)."""
    bst = block_starts(panel.time.min(), issues.max())
    by_unit = {u: g.sort_values("time") for u, g in panel.groupby("unit", sort=False)}
    bi = {u: block_indicator(g.time, g.y_start_1h.values.astype(float), bst) for u, g in by_unit.items()}
    # contexts: oblast (parent) and nation = any unit in the group had a new alert in the block
    def group_bi(units):
        st = np.vstack([bi[u] for u in units])
        out = np.nanmax(np.where(np.isnan(st), -1, st), axis=0)
        return np.where(out < 0, np.nan, out)
    nat_bi = group_bi(list(bi))
    par_bi = {p: group_bi([u for u in bi if parent_of[u] == p]) for p in set(parent_of.values())} if parent_of else {}
    k0 = np.searchsorted(bst.values, issues.values, side="left")
    lead_idx = k0[:, None] + np.arange(N_LEAD)[None, :]
    bend = np.append(bst.values[1:], bst.values[-1] + np.timedelta64(3, "h"))
    lead_h = (bst.values[lead_idx] - issues.values[:, None]) / np.timedelta64(1, "h")
    loc = bst.tz_convert(KYIV)
    slot, dow = (loc.hour.values // 3)[lead_idx], loc.dayofweek.values[lead_idx]
    after_last = bend[lead_idx] > np.datetime64(last_known.tz_convert(None))
    nat_r14, _ = rate_features(nat_bi, bst, issues, lead_idx)
    frames = []
    for u, g in by_unit.items():
        x = g.set_index("time").reindex(issues)[feats]
        r14, d4 = rate_features(bi[u], bst, issues, lead_idx)
        y = bi[u][lead_idx].copy()
        y[after_last] = np.nan
        f = pd.DataFrame(np.repeat(x.values, N_LEAD, axis=0), columns=feats)
        f["unit"], f["issue_time"] = u, np.repeat(issues.values, N_LEAD)
        f["block_start"] = bst.values[lead_idx].ravel()
        f["lead_h"], f["block_slot"], f["block_dow"] = lead_h.ravel(), slot.ravel(), dow.ravel()
        f["blk_rate14"], f["blk_dow4"], f["nat_blk_rate14"] = r14.ravel(), d4.ravel(), nat_r14.ravel()
        if parent_of:
            pr14, _ = rate_features(par_bi[parent_of[u]], bst, issues, lead_idx)
            f["parent_blk_rate14"] = pr14.ravel()
        f["y_block"] = y.ravel()
        frames.append(f)
    out = pd.concat(frames, ignore_index=True)
    out["issue_time"] = pd.to_datetime(out.issue_time, utc=True)
    out["block_start"] = pd.to_datetime(out.block_start, utc=True)
    return out


TIMING_EXTRA = ["lead_h", "block_slot", "block_dow", "blk_rate14", "blk_dow4", "nat_blk_rate14"]

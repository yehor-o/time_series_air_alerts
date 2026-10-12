"""Leakage tests (CLAUDE.md: every feature function must be checked for look-ahead).

For random cut times T we compute the panel twice:
  full  - from all alerts;
  known - from what was known at T: alerts that started after T deleted, ends after T hidden.
Every feature at every issue time t <= T must be identical. Targets are allowed to differ.
"""
import numpy as np
import pandas as pd
import pytest

from src.alerts.features import build_panel, truncate

RNG = np.random.default_rng(0)


def synthetic_alerts(n_units=4, days=40):
    rows = []
    t0 = pd.Timestamp("2026-01-01", tz="UTC")
    for u in range(n_units):
        t = t0
        while t < t0 + pd.Timedelta(days=days):
            t += pd.Timedelta(minutes=float(RNG.exponential(300)))
            d = pd.Timedelta(minutes=float(RNG.exponential(45)) + 1)
            rows.append(dict(unit=f"u{u}", oblast=f"o{u % 2}", start=t, end=t + d))
            t += d
    df = pd.DataFrame(rows)
    df.attrs["unit_cols"] = ["unit"]
    return df


def feature_cols(panel):
    return [c for c in panel.columns if not c.startswith("y_") and c not in ("time", "unit")]


def check(intervals, units, grid, parent, cut):
    last = grid[-1] + pd.Timedelta("1h")
    full = build_panel(intervals, units, grid, last, parent=parent)
    known_iv = truncate(intervals, cut)
    known_iv.attrs = intervals.attrs
    known = build_panel(known_iv, units, grid, last, parent=parent)
    cols = feature_cols(full)
    a = full[full.time <= cut][cols].reset_index(drop=True)
    b = known[known.time <= cut][cols].reset_index(drop=True)
    pd.testing.assert_frame_equal(a, b, check_exact=False, rtol=1e-9, atol=1e-9)


@pytest.mark.parametrize("seed", range(5))
def test_no_lookahead_synthetic(seed):
    iv = synthetic_alerts()
    units = sorted(iv.unit.unique())
    parent = dict(zip(iv.unit, iv.oblast))
    grid = pd.date_range("2026-01-01", "2026-02-09", freq="h", tz="UTC")
    cut = grid[np.random.default_rng(seed).integers(24 * 15, len(grid) - 24)]
    check(iv, units, grid, parent, cut)


def test_no_lookahead_real_raions():
    """Same check on real data: 6 raions of two oblasts around the reform period."""
    path = "data/processed/alerts_raion.parquet"
    try:
        r = pd.read_parquet(path)
    except FileNotFoundError:
        pytest.skip("run scripts/build_alert_table.py first")
    obs = ["Харківська область", "Київська область"]
    r = r[r.oblast.isin(obs)]
    keep = r.groupby("oblast").raion.unique().map(lambda x: list(x[:3])).sum()
    r = r[r.raion.isin(keep)].copy()
    r.attrs["unit_cols"] = ["oblast", "raion"]
    units = sorted(set(zip(r.oblast, r.raion)))
    parent = {u: u[0] for u in units}
    grid = pd.date_range("2026-08-20", "2026-10-01", freq="h", tz="UTC")
    for cut in (pd.Timestamp("2026-09-07 06:00", tz="UTC"), pd.Timestamp("2026-09-20 21:00", tz="UTC")):
        check(r, units, grid, parent, cut)


def test_targets_do_look_ahead():
    """Sanity check of the test itself: targets must change when the future is hidden."""
    iv = synthetic_alerts()
    units = sorted(iv.unit.unique())
    grid = pd.date_range("2026-01-01", "2026-02-09", freq="h", tz="UTC")
    cut = grid[24 * 20]
    last = grid[-1] + pd.Timedelta("1h")
    full = build_panel(iv, units, grid, last)
    t = truncate(iv, cut)
    t.attrs = iv.attrs
    known = build_panel(t, units, grid, last)
    day_before = lambda p: p[(p.time > cut - pd.Timedelta("24h")) & (p.time <= cut)].y_count_24h.values
    assert not np.array_equal(day_before(full), day_before(known))


def test_war_monitor_features_no_lookahead():
    """Deleting all @war_monitor posts published at or after T must not change any feature at t <= T."""
    from src.alerts.telegram import load_channel
    from src.alerts.telegram_features import war_monitor_features
    try:
        posts = load_channel("data/raw/telegram/war_monitor.jsonl")
    except Exception:
        pytest.skip("scrape @war_monitor first")
    posts = posts[(posts.published >= "2026-08-01") & (posts.published < "2026-09-15")]
    grid = pd.date_range("2026-08-10", "2026-09-14", freq="h", tz="UTC")
    obs = ["м. Київ", "Харківська область"]
    for cut in (pd.Timestamp("2026-08-20 03:00", tz="UTC"), pd.Timestamp("2026-09-07 21:00", tz="UTC")):
        n1, r1 = war_monitor_features(posts, grid, obs)
        n2, r2 = war_monitor_features(posts[posts.published < cut], grid, obs)
        pd.testing.assert_frame_equal(n1[n1.index <= cut], n2[n2.index <= cut])
        sel = lambda r: r[r.index.get_level_values("time") <= cut]
        pd.testing.assert_frame_equal(sel(r1), sel(r2))


def test_timing_rows_no_lookahead():
    """Timing-model inputs at an issue time t must not change when everything after t is hidden."""
    from src.alerts.timing import TIMING_EXTRA, issue_times, timing_rows
    iv = synthetic_alerts()
    units = sorted(iv.unit.unique())
    parent = dict(zip(iv.unit, iv.oblast))
    grid = pd.date_range("2026-01-01", "2026-02-09", freq="h", tz="UTC")
    last = grid[-1] + pd.Timedelta("1h")
    feats = ["active", "starts_24h", "hod_rate14"]
    cut = pd.Timestamp("2026-01-25 22:00", tz="UTC")  # 00:00 Kyiv
    iss = issue_times(cut, cut)

    def rows(intervals):
        p = build_panel(intervals, units, grid, last, parent=parent)
        return timing_rows(p, feats, iss, last, parent_of=parent)

    known = truncate(iv, cut)
    known.attrs = iv.attrs
    cols = feats + TIMING_EXTRA + ["parent_blk_rate14"]
    pd.testing.assert_frame_equal(rows(iv)[cols], rows(known)[cols])

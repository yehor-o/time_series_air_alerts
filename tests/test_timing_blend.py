"""D45 blend: weights, bounds, and that the pattern input does not look into the future."""
import numpy as np
import pandas as pd

from src.alerts.timing import BLEND_HORIZON_H, block_indicator, block_starts, blend_timing, blend_weight, rate_features


def test_weights():
    assert blend_weight(0) == 1.0
    assert blend_weight(BLEND_HORIZON_H / 2) == 0.5
    assert blend_weight(BLEND_HORIZON_H) == 0.0
    assert blend_weight(167) == 0.0


def test_blend_between_inputs_and_valid():
    rng = np.random.default_rng(0)
    pm, pp, lead = rng.random(500), rng.random(500), rng.uniform(0, 168, 500)
    out = blend_timing(pm, pp, lead)
    assert np.all(out >= np.minimum(pm, pp) - 1e-12) and np.all(out <= np.maximum(pm, pp) + 1e-12)
    assert np.all((out >= 0) & (out <= 1))
    np.testing.assert_allclose(blend_timing(pm, pp, np.full(500, 100.0)), pp)  # far blocks = pattern rule
    np.testing.assert_allclose(blend_timing(pm, pp, np.zeros(500)), pm)        # lead 0 = model


def test_pattern_rule_ignores_future():
    """blk_rate14 at issue time t must not change if everything after t is deleted."""
    rng = np.random.default_rng(1)
    hours = pd.date_range("2026-01-01", periods=24 * 40, freq="h", tz="UTC")
    starts = (rng.random(len(hours)) < 0.05).astype(float)
    issue = pd.DatetimeIndex([hours[24 * 25]])
    lead_idx_for = lambda bst: (np.searchsorted(bst.values, issue.values, side="left")[:, None] + np.arange(56)[None, :])

    bst = block_starts(hours.min(), hours.max())
    full = block_indicator(hours, starts, bst)
    cut = hours <= issue[0]  # only hours known at t (end hour excluded below by block rule)
    bst2 = block_starts(hours.min(), hours.max())
    part = block_indicator(hours[cut], starts[cut], bst2)
    r_full, d_full = rate_features(full, bst, issue, lead_idx_for(bst))
    r_part, d_part = rate_features(part, bst2, issue, lead_idx_for(bst2))
    np.testing.assert_allclose(r_full, r_part, equal_nan=True)
    np.testing.assert_allclose(d_full, d_part, equal_nan=True)

"""Forecast check (D60): a block that started before the forecast moment is scored only on its hours from that moment on,
so an alert that started before the forecast never counts as a "hit" or "miss" of that forecast."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from forecast_check import score  # noqa: E402

T = lambda s: pd.Timestamp(s, tz="UTC")


def setup(start_hours):
    """One district; new alerts start in the given hours (UTC) of 2026-10-13."""
    grid = pd.date_range(T("2026-10-13 00:00"), T("2026-10-15 00:00"), freq="h")
    y = np.isin(grid.hour + 24 * (grid.day - 13), start_hours).astype(float)
    pan = pd.DataFrame({"time": grid, "unit": "U", "y_start_1h": y, "y_count_24h": 0.0, "y_hours_24h": 0.0})
    empty = pd.DataFrame({"unit": pd.Series(dtype=str), "start": pd.Series(dtype="datetime64[ns, UTC]"),
                          "end": pd.Series(dtype="datetime64[ns, UTC]"), "red": pd.Series(dtype=object)})
    fc = {"p1": 0.1, "p3": 0.2, "cnt": [0, 1], "hrs": [0, 1], "next24": [0.5] * 8}
    snap = {"forecast_time_utc": "2026-10-13T11:00:00+00:00",
            "block_starts_utc": [(T("2026-10-13 09:00") + pd.Timedelta(hours=3 * k)).isoformat() for k in range(8)],
            "raion": {"U": fc}, "oblast": {"U": fc}}
    return score(snap, {"raion": pan, "oblast": pan}, {"raion": empty, "oblast": empty}, T("2026-10-15 00:00"))


def test_hours_before_the_forecast_do_not_count():
    r = setup([9])  # alert started at 09:00, forecast made at 11:00; the first block is 09:00-12:00
    assert r["raion"]["U"]["actual_blocks"][0] == 0


def test_hours_after_the_forecast_in_the_first_block_count():
    r = setup([11])  # started at 11:00, inside the part of the first block after the forecast
    assert r["raion"]["U"]["actual_blocks"][0] == 1
    assert r["raion"]["U"]["actual_blocks"][1:] == [0] * 7

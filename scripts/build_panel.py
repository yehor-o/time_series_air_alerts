"""Build the hourly forecasting tables (Task 2) and the yellow/red event table.

Outputs data/processed/panel_raion.parquet   one row per (raion, hour): features + targets
        data/processed/panel_oblast.parquet  one row per (oblast, hour)
        data/processed/red_events.parquet    one row per raion alert since the reform: features at the
                                             issue hour before it started + target red (D24)

Usage: PYTHONPATH=. python scripts/build_panel.py [--start 2024-01-01]
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src.alerts.features import build_panel
from src.alerts.sources import ARCHIVE_COMPLETE_FROM

P = Path("data/processed")


def red_features(events, t, unit_col, unit, parent_col=None, parent=None):
    """Level features at issue time t from alerts that started before t (levels are known at the start)."""
    past = events[(events.start < t) & events.red.notna()]
    out = {}
    mine = past[past[unit_col] == unit]
    out["prev_red"] = float(mine.red.iloc[-1]) if len(mine) else np.nan
    out["unit_red_share_7d"] = mine[mine.start >= t - pd.Timedelta("7D")].red.astype(float).mean()
    if parent_col:
        par = past[(past[parent_col] == parent) & (past.start >= t - pd.Timedelta("24h"))]
        out["parent_red_share_24h"] = par.red.astype(float).mean()
    for w in ("3h", "24h"):
        n = past[past.start >= t - pd.Timedelta(w)]
        out[f"nat_red_share_{w}"] = n.red.astype(float).mean()
        out[f"nat_red_count_{w}"] = float(n.red.sum())
    return out


def main(start):
    raion = pd.read_parquet(P / "alerts_raion.parquet")
    oblast = pd.read_parquet(P / "alerts_oblast.parquet")
    masks = pd.read_parquet(P / "masks.parquet")
    universe = pd.read_csv(P / "raions.csv")
    last_known = raion.start.max().ceil("min")
    grid = pd.date_range(pd.Timestamp(start, tz="UTC"), last_known.floor("h"), freq="h")
    print(f"grid {grid[0]} .. {grid[-1]} ({len(grid)} hours), last known {last_known}")

    raion.attrs["unit_cols"] = ["oblast", "raion"]
    units = list(zip(universe.oblast, universe.raion))
    pr = build_panel(raion, units, grid, last_known, parent={u: u[0] for u in units}, masks=masks)
    pr["oblast"] = pr.unit.str.split("|").str[0]
    pr.to_parquet(P / "panel_raion.parquet")
    print("panel_raion", pr.shape)

    oblast = oblast.rename(columns={"oblast": "unit"})
    oblast.attrs["unit_cols"] = ["unit"]
    po = build_panel(oblast, sorted(universe.oblast.unique()), grid, last_known)  # oblast truth has no masks
    po["oblast"] = po.unit
    po.to_parquet(P / "panel_oblast.parquet")
    print("panel_oblast", po.shape)

    # yellow/red events: raion alerts with a level, issue time = the hour before they started
    ev = raion[raion.red.notna() & (raion.start >= ARCHIVE_COMPLETE_FROM)].sort_values("start").copy()
    ev["unit"] = ev.oblast + "|" + ev.raion
    ev["time"] = ev.start.dt.floor("h")
    allev = raion[raion.red.notna()].sort_values("start").assign(unit=lambda d: d.oblast + "|" + d.raion)
    rows = [red_features(allev, r.time, "unit", r.unit, "oblast", r.oblast) for r in ev.itertuples()]
    ev = pd.concat([ev.reset_index(drop=True), pd.DataFrame(rows)], axis=1)
    ev = ev.merge(pr.drop(columns=[c for c in pr.columns if c.startswith("y_")] + ["oblast"]), on=["unit", "time"], how="left")
    ev["y_red"] = ev.red.astype(float)
    ev.to_parquet(P / "red_events.parquet")
    print("red_events", ev.shape, "share red", round(ev.y_red.mean(), 3))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2024-01-01")
    main(ap.parse_args().start)

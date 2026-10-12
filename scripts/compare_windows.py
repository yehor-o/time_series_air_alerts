"""How much history should the models learn from? (user question 2026-10-12, D7)

Same LightGBM, same features, same 4 weekly validation folds as scripts/validate_models.py; only the
training rows change:
  full history (since 2022-04), since 2024, 24 / 12 / 6 / 3 months,
  full history with recency weights (each row's weight halves every 6 or 12 months back in time).
The test period (from 2026-09-13) is not used.

Usage: PYTHONPATH=. python scripts/compare_windows.py
Output: reports/training_window.md
"""
import time
from pathlib import Path

import numpy as np
import pandas as pd

from validate_models import (BASE_FEATS, PARENT_FEATS, TEST_START, cls_scores, folds, lgb_cls, mean_table)

P, REP = Path("data/processed"), Path("reports")
FIRST = pd.Timestamp("2022-04-01", tz="UTC")  # 30 days of warm-up after the first data
WINDOWS = {  # name -> (start of training rows or a lookback, half-life for recency weights)
    "full history (2022-04 on)": (None, None),
    "since 2024-01": (pd.Timestamp("2024-01-31", tz="UTC"), None),
    "last 24 months": (pd.Timedelta("730D"), None),
    "last 12 months": (pd.Timedelta("365D"), None),
    "last 6 months": (pd.Timedelta("182D"), None),
    "last 3 months": (pd.Timedelta("91D"), None),
    "full, recency-weighted (half-life 12 months)": (None, 365),
    "full, recency-weighted (half-life 6 months)": (None, 182),
}
# time budget (deadline day): the raion level runs a reduced set on the last 2 folds, 3h horizon only
RAION_WINDOWS = ["full history (2022-04 on)", "since 2024-01", "last 12 months", "full, recency-weighted (half-life 12 months)"]
OBLAST_WINDOWS = [w for w in WINDOWS if w not in ("last 24 months", "full, recency-weighted (half-life 6 months)")]


def train_rows(d, lo, purge_h, spec):
    start, hl = spec
    tr = d[(d.time < lo - pd.Timedelta(hours=purge_h)) & (d.time >= FIRST)]
    if isinstance(start, pd.Timestamp):
        tr = tr[tr.time >= start]
    elif isinstance(start, pd.Timedelta):
        tr = tr[tr.time >= lo - start]
    w = None if hl is None else 0.5 ** ((lo - tr.time).dt.total_seconds() / 86400 / hl)
    return tr, w


def main():
    t0 = time.time()
    log = lambda m: print(f"[{time.time() - t0:6.0f}s] {m}", flush=True)
    po = pd.read_parquet(P / "panel_oblast.parquet")
    pr = pd.read_parquet(P / "panel_raion.parquet")
    last = po.time.max() + pd.Timedelta("1h")
    test_start = TEST_START
    codes = {o: i for i, o in enumerate(sorted(po.oblast.unique()))}
    md = ["# Training window: how much history should the models learn from?\n",
          f"Same LightGBM and features; 4 weekly validation folds ({', '.join(f'{a:%b %d}' for a, _ in folds(test_start))}); "
          f"the test period from {test_start:%Y-%m-%d} is untouched. Averages over the folds. "
          "Skill = Brier improvement over the 'same hour, last 14 days' rule.\n"]
    for name, df, feats in (("oblast", po, BASE_FEATS), ("raion", pr, BASE_FEATS + PARENT_FEATS)):
        df = df[df.time < test_start].copy()
        df["oblast_code"] = df.oblast.map(codes).astype("category")
        horizons, fold_list, wins = ((1, 3), folds(test_start), OBLAST_WINDOWS) if name == "oblast" else \
            ((3,), folds(test_start)[-2:], RAION_WINDOWS)
        for h in horizons:
            y = f"y_start_{h}h"
            d = df[df[y].notna()]
            rows = []
            for lo, hi in fold_list:
                va = d[(d.time >= lo) & (d.time < hi)]
                for wname in wins:
                    spec = WINDOWS[wname]
                    tr, w = train_rows(d, lo, h, spec)
                    g = lgb_cls().fit(tr[feats], tr[y], sample_weight=w, categorical_feature=["oblast_code"])
                    rows.append({"model": wname, "training rows": len(tr),
                                 **cls_scores(va[y], g.predict_proba(va[feats])[:, 1], va.hod_rate14.values)})
                log(f"{name} {h}h fold {lo:%m-%d}")
            t = mean_table(rows)
            t["training rows"] = t["training rows"].round(-3).astype(int)
            md += [f"## {name.title()}: new alert within {h}h ({len(fold_list)} folds)\n", "```\n" + t.round(4).to_string() + "\n```\n"]
            (REP / "training_window.md").write_text("\n".join(md), encoding="utf-8")
    log("done")


if __name__ == "__main__":
    main()

"""Validate the timing model (plan C, D42): 56 Kyiv-time 3-hour blocks of the next 7 days.

Training history follows D40 (raion: last 12 months; oblast: last 24 months, recency half-life 12 months
- shorter than "full" to keep the long table manageable on deadline day). Forecasts are issued at
00:00 and 12:00 Kyiv. Validation on the last 2 weekly folds before the test period (Aug 30 – Sep 12);
training issue times are purged so every training block ended before the fold starts.

Reported per lead day (day 1 = the first 8 blocks = "next 24h") against the pattern rule
"share of the last 14 days with a new alert in this clock block" (blk_rate14).

Usage: PYTHONPATH=.:scripts python scripts/validate_timing.py
Output: reports/timing_validation.md
"""
import time
from pathlib import Path

import numpy as np
import pandas as pd

from src.alerts.timing import TIMING_EXTRA, issue_times, timing_rows
from validate_models import BASE_FEATS, PARENT_FEATS, cls_scores, folds, lgb_cls, TEST_START

P, REP = Path("data/processed"), Path("reports")


def main():
    t0 = time.time()
    log = lambda m: print(f"[{time.time() - t0:6.0f}s] {m}", flush=True)
    md = ["# Timing model: when in the next 7 days? (validation)\n",
          "One LightGBM predicts, for each 3-hour Kyiv-time block of the next 7 days, the chance that a new alert "
          "starts in it. Forecasts issued at 00:00 and 12:00 Kyiv. Last 2 validation weeks (Aug 30 – Sep 12 2026); the "
          "test period is untouched. **Pattern rule** = share of the last 14 days with a new alert in the same clock "
          "block. Skill = Brier improvement over the pattern rule.\n"]
    for level, hist_days, hl in (("raion", 365, None), ("oblast", 730, 365)):
        pan = pd.read_parquet(P / f"panel_{level}.parquet")
        last_known = pan.time.max() + pd.Timedelta("1h")
        test_start = TEST_START
        fl = folds(test_start)[-2:]
        start = fl[0][0] - pd.Timedelta(days=hist_days + 30)
        pan = pan[(pan.time >= start) & (pan.time < test_start)]
        feats = BASE_FEATS + (PARENT_FEATS if level == "raion" else [])
        feats = [f for f in feats if f != "oblast_code"]
        parent = dict(zip(pan.unit, pan.oblast)) if level == "raion" else None
        iss = issue_times(start + pd.Timedelta("20D"), test_start - pd.Timedelta("1h"))
        rows = timing_rows(pan, feats, iss, test_start, parent_of=parent)
        rows["oblast_code"] = rows.unit.str.split("|").str[0].astype("category")
        X = feats + TIMING_EXTRA + (["parent_blk_rate14"] if level == "raion" else []) + ["oblast_code"]
        num = [c for c in X if c != "oblast_code"]
        rows[num] = rows[num].astype("float32")
        rows = rows[rows.y_block.notna()]
        log(f"{level}: {len(rows):,} timing rows")
        res, per_day = [], []
        for lo, hi in fl:
            tr = rows[(rows.block_start + pd.Timedelta("3h") <= lo) & (rows.issue_time >= lo - pd.Timedelta(days=hist_days))]
            va = rows[(rows.issue_time >= lo) & (rows.issue_time < hi)]
            w = None if hl is None else 0.5 ** ((lo - tr.issue_time).dt.total_seconds() / 86400 / hl)
            g = lgb_cls(n_estimators=300).fit(tr[X], tr.y_block, sample_weight=w, categorical_feature=["oblast_code"])
            p = g.predict_proba(va[X])[:, 1]
            base = va.blk_rate14.fillna(tr.y_block.mean()).values
            res += [{"model": "pattern rule (same block, last 14 days)", **cls_scores(va.y_block, base, base)},
                    {"model": "LightGBM timing model", **cls_scores(va.y_block, p, base)}]
            day = (va.lead_h.values // 24).astype(int) + 1
            for d in range(1, 8):
                m = day == d
                if m.sum() and len(set(va.y_block[m])) > 1:
                    per_day.append({"model": f"day {d}", "pattern AUC": cls_scores(va.y_block[m], base[m])["ROC-AUC"],
                                    **{f"model {k}": v for k, v in cls_scores(va.y_block[m], p[m], base[m]).items()}})
            log(f"{level} fold {lo:%m-%d}")
        t = pd.DataFrame(res).groupby("model", sort=False).mean()
        d = pd.DataFrame(per_day).groupby("model", sort=False).mean()[["pattern AUC", "model ROC-AUC", "model skill vs same-hour", "model Brier"]]
        d = d.rename(columns={"model skill vs same-hour": "model skill vs pattern"})
        md += [f"## {level.title()}\n", "All 56 blocks:\n", "```\n" + t.round(4).to_string() + "\n```\n",
               "By how far ahead (day 1 = next 24 hours):\n", "```\n" + d.round(3).to_string() + "\n```\n"]
        (REP / "timing_validation.md").write_text("\n".join(md), encoding="utf-8")
        del rows
    log("done")


if __name__ == "__main__":
    main()

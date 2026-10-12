"""With vs without Telegram (@war_monitor) — task D, the ablation for the "How good is it?" page.

Same folds as validation (4 weeks before the test period, untouched test), the accepted training
history (D40: raion = last 12 months, oblast = full history with recency weights, half-life 12 months),
the same LightGBM; the only difference between the two arms is the 26 @war_monitor features
(src/alerts/telegram_features.py, posts published before the forecast time only).

Usage: PYTHONPATH=.:scripts python scripts/compare_telegram.py
Output: reports/telegram_ablation.md
"""
import time
from pathlib import Path

import numpy as np
import pandas as pd

from src.alerts.telegram import load_channel
from src.alerts.telegram_features import add_war_monitor, war_monitor_features
from validate_models import BASE_FEATS, PARENT_FEATS, cls_scores, folds, lgb_cls, lgb_reg, mean_table, TEST_START

P, REP = Path("data/processed"), Path("reports")
FIRST = pd.Timestamp("2022-04-01", tz="UTC")


def training(d, lo, purge_h, level):
    """D40: raion = last 12 months; oblast = full history, weight 0.5 ** (age_days / 365)."""
    tr = d[(d.time < lo - pd.Timedelta(hours=purge_h)) & (d.time >= FIRST)]
    if level == "raion":
        return tr[tr.time >= lo - pd.Timedelta("365D")], None
    age_days = (lo - tr.time).dt.total_seconds() / 86400
    return tr, 0.5 ** (age_days / 365)


def main():
    t0 = time.time()
    log = lambda m: print(f"[{time.time() - t0:6.0f}s] {m}", flush=True)
    wm = load_channel("data/raw/telegram/war_monitor.jsonl")
    md = ["# With vs without Telegram (@war_monitor)\n",
          "Same model, same data, same 4 validation weeks (Aug 16 – Sep 12 2026; the test period is untouched). "
          "The only difference: the second model also sees 26 features computed from @war_monitor posts published "
          "**before** the forecast time (drone / missile / guided-bomb posts in the last 3, 6, 24 h, drone counts "
          "written in posts, strategic-aviation status, posts naming the oblast, channel silence).\n",
          "Rule agreed with the user: the map uses the Telegram version only if it wins on these weeks.\n"]
    for level in ("raion", "oblast"):
        df = pd.read_parquet(P / f"panel_{level}.parquet")
        last = df.time.max() + pd.Timedelta("1h")
        test_start = TEST_START
        start = folds(test_start)[0][0] - pd.Timedelta("400D") if level == "raion" else FIRST
        df = df[(df.time >= start) & (df.time < test_start)].copy()
        df["oblast_code"] = df.oblast.astype("category")
        grid = pd.DatetimeIndex(sorted(df.time.unique()))
        nat, reg = war_monitor_features(wm, grid, sorted(df.oblast.unique()))
        df = add_war_monitor(df, nat, reg)
        wm_feats = list(nat.columns) + list(reg.columns)
        feats = BASE_FEATS + (PARENT_FEATS if level == "raion" else [])
        log(f"{level}: features ready, {len(df):,} rows")
        md.append(f"## {level.title()}\n")
        for h in (1, 3):
            y, rows = f"y_start_{h}h", []
            d = df[df[y].notna()]
            for lo, hi in folds(test_start):
                tr, w = training(d, lo, h, level)
                va = d[(d.time >= lo) & (d.time < hi)]
                for name, f in (("without Telegram", feats), ("with Telegram", feats + wm_feats)):
                    p = lgb_cls().fit(tr[f], tr[y], sample_weight=w, categorical_feature=["oblast_code"]).predict_proba(va[f])[:, 1]
                    rows.append({"model": name, **cls_scores(va[y], p, va.hod_rate14.values)})
                log(f"{level} {h}h fold {lo:%m-%d}")
            md += [f"New alert within {h}h:\n", "```\n" + mean_table(rows).round(4).to_string() + "\n```\n"]
            (REP / "telegram_ablation.md").write_text("\n".join(md), encoding="utf-8")
        rows = []
        d = df[df.y_count_24h.notna()]
        for lo, hi in folds(test_start):
            tr, w = training(d, lo, 24, level)
            va = d[(d.time >= lo) & (d.time < hi)]
            for name, f in (("without Telegram", feats), ("with Telegram", feats + wm_feats)):
                c = lgb_reg(objective="poisson", n_estimators=200).fit(tr[f], tr.y_count_24h, sample_weight=w,
                                                                       categorical_feature=["oblast_code"]).predict(va[f])
                hh = lgb_reg(objective="l1", n_estimators=200).fit(tr[f], tr.y_hours_24h, sample_weight=w,
                                                                   categorical_feature=["oblast_code"]).predict(va[f])
                rows.append({"model": name, "count MAE": np.mean(np.abs(va.y_count_24h - c)),
                             "hours MAE": np.mean(np.abs(va.y_hours_24h - np.clip(hh, 0, 24)))})
            log(f"{level} 24h fold {lo:%m-%d}")
        md += ["Next 24h, number of alerts and hours under alert (average error):\n",
               "```\n" + mean_table(rows).round(3).to_string() + "\n```\n"]
        (REP / "telegram_ablation.md").write_text("\n".join(md), encoding="utf-8")
    log("done")


if __name__ == "__main__":
    main()

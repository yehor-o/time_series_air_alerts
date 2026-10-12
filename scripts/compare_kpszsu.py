"""With vs without @kpszsu (Air Force channel) — same protocol as compare_telegram.py (@war_monitor).

Same folds (4 weeks before the untouched test period), same accepted training history (D40), same LightGBM.
The only difference between the arms: the @kpszsu features (src/alerts/telegram_features.py with the
@war_monitor tagger, columns renamed kp_*; posts published before the forecast time only).
@kpszsu starts on 2025-08-31, so every kp_* feature is NaN (unknown, not "quiet") before its first post + 24 h.
The strategic-aviation feature is @war_monitor-specific and dropped.

Rule (D44): the map uses the Telegram version only if it wins on these weeks.

Usage: PYTHONPATH=.:scripts python scripts/compare_kpszsu.py
Output: reports/kpszsu_ablation.md
"""
import time
from pathlib import Path

import numpy as np
import pandas as pd

from compare_telegram import FIRST, training
from src.alerts.telegram import load_channel
from src.alerts.telegram_features import add_war_monitor, war_monitor_features
from validate_models import BASE_FEATS, PARENT_FEATS, cls_scores, folds, lgb_cls, lgb_reg, mean_table

P, REP = Path("data/processed"), Path("reports")


def kpszsu_features(posts, grid, oblasts):
    nat, reg = war_monitor_features(posts, grid, oblasts)
    nat = nat.drop(columns="wm_strat_aviation").rename(columns=lambda c: c.replace("wm_", "kp_"))
    reg = reg.rename(columns=lambda c: c.replace("wm_", "kp_"))
    covered = pd.DatetimeIndex(grid) >= posts.published.min() + pd.Timedelta("24h")
    nat.loc[~covered, :] = np.nan
    reg = reg.copy()
    reg.loc[~reg.index.get_level_values("time").isin(pd.DatetimeIndex(grid)[covered]), :] = np.nan
    return nat, reg


def main():
    t0 = time.time()
    log = lambda m: print(f"[{time.time() - t0:6.0f}s] {m}", flush=True)
    kp = load_channel("data/raw/telegram/kpszsu/part*.jsonl")
    log(f"@kpszsu: {len(kp):,} posts {kp.published.min():%Y-%m-%d} .. {kp.published.max():%Y-%m-%d}, "
        f"edited {kp.edited.mean():.1%}")
    md = ["# With vs without @kpszsu\n",
          "Same model, data and 4 validation weeks as the @war_monitor test (Aug 16 – Sep 12 2026; the test period is "
          "untouched). The second model also sees 25 features from @kpszsu posts published **before** the forecast "
          "time (drone / missile / guided-bomb posts in the last 3, 6, 24 h, drone counts, posts naming the oblast, "
          "channel silence). @kpszsu covers 2025-08-31 onward; earlier hours are 'unknown', not 'quiet'. "
          f"{len(kp):,} posts, {kp.edited.mean():.1%} flagged as edited (kept, as for @war_monitor).\n",
          "Rule (D44): the map uses the Telegram version only if it wins on these weeks.\n"]
    for level in ("raion", "oblast"):
        df = pd.read_parquet(P / f"panel_{level}.parquet")
        last = df.time.max() + pd.Timedelta("1h")
        test_start = (last - pd.Timedelta("28D")).floor("D")
        start = folds(test_start)[0][0] - pd.Timedelta("400D") if level == "raion" else FIRST
        df = df[(df.time >= start) & (df.time < test_start)].copy()
        df["oblast_code"] = df.oblast.astype("category")
        grid = pd.DatetimeIndex(sorted(df.time.unique()))
        nat, reg = kpszsu_features(kp, grid, sorted(df.oblast.unique()))
        df = add_war_monitor(df, nat, reg)
        kp_feats = list(nat.columns) + list(reg.columns)
        feats = BASE_FEATS + (PARENT_FEATS if level == "raion" else [])
        log(f"{level}: features ready, {len(df):,} rows")
        md.append(f"## {level.title()}\n")
        for h in (1, 3):
            y, rows = f"y_start_{h}h", []
            d = df[df[y].notna()]
            for lo, hi in folds(test_start):
                tr, w = training(d, lo, h, level)
                va = d[(d.time >= lo) & (d.time < hi)]
                for name, f in (("without @kpszsu", feats), ("with @kpszsu", feats + kp_feats)):
                    p = lgb_cls().fit(tr[f], tr[y], sample_weight=w, categorical_feature=["oblast_code"]).predict_proba(va[f])[:, 1]
                    rows.append({"model": name, **cls_scores(va[y], p, va.hod_rate14.values)})
                log(f"{level} {h}h fold {lo:%m-%d}")
            md += [f"New alert within {h}h:\n", "```\n" + mean_table(rows).round(4).to_string() + "\n```\n"]
            (REP / "kpszsu_ablation.md").write_text("\n".join(md), encoding="utf-8")
        rows = []
        d = df[df.y_count_24h.notna()]
        for lo, hi in folds(test_start):
            tr, w = training(d, lo, 24, level)
            va = d[(d.time >= lo) & (d.time < hi)]
            for name, f in (("without @kpszsu", feats), ("with @kpszsu", feats + kp_feats)):
                c = lgb_reg(objective="poisson", n_estimators=200).fit(tr[f], tr.y_count_24h, sample_weight=w,
                                                                       categorical_feature=["oblast_code"]).predict(va[f])
                hh = lgb_reg(objective="l1", n_estimators=200).fit(tr[f], tr.y_hours_24h, sample_weight=w,
                                                                   categorical_feature=["oblast_code"]).predict(va[f])
                rows.append({"model": name, "count MAE": np.mean(np.abs(va.y_count_24h - c)),
                             "hours MAE": np.mean(np.abs(va.y_hours_24h - np.clip(hh, 0, 24)))})
            log(f"{level} 24h fold {lo:%m-%d}")
        md += ["Next 24h, number of alerts and hours under alert (average error):\n",
               "```\n" + mean_table(rows).round(3).to_string() + "\n```\n"]
        (REP / "kpszsu_ablation.md").write_text("\n".join(md), encoding="utf-8")
    log("done")


if __name__ == "__main__":
    main()

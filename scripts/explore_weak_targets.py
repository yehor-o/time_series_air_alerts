"""Exploring the weak targets (duration, 24h count, 24h hours) and how to strengthen them.

Oblast panel, the same 4 weekly validation folds as scripts/validate_models.py, training rows since
2024-01-31. The test period is not used.

Ideas tested
  1. fairer baselines: "average of the last 7 days" instead of "same as the last 24h";
  2. duration as a RANGE: quantile models (25th/50th/75th percentile) and duration bands, scored by
     pinball loss and by how often the true duration falls into the predicted 25-75% range (ideal: 50%);
  3. @war_monitor threat features (src/alerts/telegram_features.py), also checked on the strong
     "new alert within 3h" target (Telegram ablation).

Usage: PYTHONPATH=.:scripts python scripts/explore_weak_targets.py
Output: reports/weak_targets.md
"""
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

from src.alerts.telegram import load_channel
from src.alerts.telegram_features import war_monitor_features, add_war_monitor
from validate_models import BASE_FEATS, LGB_CLS, cls_scores, folds, lgb_cls, lgb_reg, mean_table, split, TEST_START

P, REP = Path("data/processed"), Path("reports")
FIRST = pd.Timestamp("2024-01-31", tz="UTC")
BANDS = [0, 30, 60, 120, 240, np.inf]
BAND_NAMES = ["<30 min", "30-60 min", "1-2 h", "2-4 h", ">4 h"]


def recent_duration_quantiles(alerts, panel):
    """25th/75th percentile and band shares of the unit's last 10 ENDED alerts before t."""
    out = []
    for u, g in panel.groupby("unit", sort=False):
        a = alerts[alerts.unit == u].sort_values("end")
        ends = a.end.values.astype("datetime64[ns]")
        durs = a.duration_min.values
        j = np.searchsorted(ends, g.time.dt.tz_convert(None).values.astype("datetime64[ns]"), side="right")
        q = {n: (np.quantile(durs[max(n - 10, 0):n], [.25, .75]) if n else (np.nan, np.nan)) for n in np.unique(j)}
        bands = {n: (np.histogram(durs[max(n - 30, 0):n], BANDS)[0] / max(min(n, 30), 1)) for n in np.unique(j)}
        out.append(pd.DataFrame({"q25_last10": [q[n][0] for n in j], "q75_last10": [q[n][1] for n in j],
                                 **{f"band{b}_last30": [bands[n][b] for n in j] for b in range(5)}}, index=g.index))
    return pd.concat(out)


def pinball(y, q, a):
    d = y - q
    return np.mean(np.maximum(a * d, (a - 1) * d))


def duration_block(d, feats, wm_feats, test_start):
    rows, band_rows = [], []
    for lo, hi in folds(test_start):
        tr, va = split(d, lo, hi, 3 + 72, first=FIRST)
        y, yt = va.y_dur_3h.values, tr.y_dur_3h.values
        base = {"q25": va.q25_last10.fillna(np.quantile(yt, .25)).values, "q50": va.med_dur10.fillna(np.median(yt)).values,
                "q75": va.q75_last10.fillna(np.quantile(yt, .75)).values}
        preds = {"baseline: last 10 alerts of the oblast": base}
        for name, f in (("LightGBM quantiles", feats), ("LightGBM quantiles + @war_monitor", feats + wm_feats)):
            preds[name] = {f"q{int(a * 100)}": lgb_reg(objective="quantile", alpha=a, n_estimators=300)
                           .fit(tr[f], yt, categorical_feature=["oblast_code"]).predict(va[f]) for a in (.25, .5, .75)}
        for name, p in preds.items():
            lo_, hi_ = np.minimum(p["q25"], p["q75"]), np.maximum(p["q25"], p["q75"])
            rows.append({"model": name, "median abs error (min)": np.median(np.abs(y - p["q50"])),
                         "pinball loss (avg of 3 quantiles)": np.mean([pinball(y, p[k], a) for k, a in (("q25", .25), ("q50", .5), ("q75", .75))]),
                         "true duration inside predicted 25-75% range": np.mean((y >= lo_) & (y <= hi_)),
                         "average range width (min)": np.mean(hi_ - lo_)})
        # bands: multi-class
        yb, ytb = np.digitize(y, BANDS[1:-1]), np.digitize(yt, BANDS[1:-1])
        bp = va[[f"band{b}_last30" for b in range(5)]].values
        bp = np.where(np.isnan(bp).any(1, keepdims=True), np.bincount(ytb, minlength=5) / len(ytb), bp)
        band_preds = {"baseline: band shares of last 30 alerts": bp}
        for name, f in (("LightGBM bands", feats), ("LightGBM bands + @war_monitor", feats + wm_feats)):
            m = lgb.LGBMClassifier(**{**LGB_CLS, "n_estimators": 300, "objective": "multiclass"}).fit(tr[f], ytb, categorical_feature=["oblast_code"])
            band_preds[name] = m.predict_proba(va[f])
        for name, p in band_preds.items():
            p = np.clip(p, 1e-4, 1)
            p = p / p.sum(1, keepdims=True)
            band_rows.append({"model": name, "accuracy (most likely band)": np.mean(p.argmax(1) == yb),
                              "log-loss": -np.mean(np.log(p[np.arange(len(yb)), yb]))})
    return mean_table(rows), mean_table(band_rows)


def count_hours_block(d, feats, wm_feats, test_start):
    rows_c, rows_h = [], []
    for lo, hi in folds(test_start):
        tr, va = split(d, lo, hi, 24, first=FIRST)
        rows_c += [{"model": "baseline: same as last 24h", "MAE": np.mean(np.abs(va.y_count_24h - va.starts_24h))},
                   {"model": "baseline: daily average of last 7 days", "MAE": np.mean(np.abs(va.y_count_24h - va.starts_168h / 7))}]
        rows_h += [{"model": "baseline: same as last 24h", "MAE": np.mean(np.abs(va.y_hours_24h - va.alert_h_24h))},
                   {"model": "baseline: daily average of last 7 days", "MAE": np.mean(np.abs(va.y_hours_24h - va.alert_h_168h / 7))}]
        for name, f in (("LightGBM", feats), ("LightGBM + @war_monitor", feats + wm_feats)):
            c = lgb_reg(objective="poisson", n_estimators=200).fit(tr[f], tr.y_count_24h, categorical_feature=["oblast_code"]).predict(va[f])
            h = np.clip(lgb_reg(objective="l1", n_estimators=200).fit(tr[f], tr.y_hours_24h, categorical_feature=["oblast_code"]).predict(va[f]), 0, 24)
            rows_c.append({"model": name, "MAE": np.mean(np.abs(va.y_count_24h - c))})
            rows_h.append({"model": name, "MAE": np.mean(np.abs(va.y_hours_24h - h))})
    tc, th = mean_table(rows_c), mean_table(rows_h)
    for t in (tc, th):
        t["skill vs 7-day average"] = 1 - t.MAE / t.loc["baseline: daily average of last 7 days", "MAE"]
    return tc, th


def start_block(d, feats, wm_feats, test_start):
    rows = []
    for lo, hi in folds(test_start):
        tr, va = split(d, lo, hi, 3, first=FIRST)
        for name, f in (("LightGBM", feats), ("LightGBM + @war_monitor", feats + wm_feats)):
            p = lgb_cls(n_estimators=200).fit(tr[f], tr.y_start_3h, categorical_feature=["oblast_code"]).predict_proba(va[f])[:, 1]
            rows.append({"model": name, **cls_scores(va.y_start_3h, p, va.hod_rate14.values)})
    return mean_table(rows)


def main():
    t0 = time.time()
    log = lambda m: print(f"[{time.time() - t0:6.0f}s] {m}", flush=True)
    po = pd.read_parquet(P / "panel_oblast.parquet")
    last = po.time.max() + pd.Timedelta("1h")
    test_start = TEST_START
    po = po[(po.time >= FIRST - pd.Timedelta("1D")) & (po.time < test_start)].copy()
    codes = {o: i for i, o in enumerate(sorted(po.oblast.unique()))}
    po["oblast_code"] = po.oblast.map(codes).astype("category")
    grid = pd.DatetimeIndex(sorted(po.time.unique()))
    nat, reg = war_monitor_features(load_channel("data/raw/telegram/war_monitor.jsonl"), grid, sorted(po.oblast.unique()))
    po = add_war_monitor(po, nat, reg)
    wm_feats = list(nat.columns) + list(reg.columns)
    log("features ready")

    alerts = pd.read_parquet(P / "alerts_oblast.parquet").rename(columns={"oblast": "unit"})
    dur = po[po.y_dur_3h.notna() & (po.y_dur_3h > 0)].copy()
    dur = dur.join(recent_duration_quantiles(alerts, dur))
    md = ["# Weak targets: diagnosis and attempts to strengthen them\n",
          "Oblast level, 4 weekly validation folds (Aug 16 – Sep 12 2026), training rows since 2024-01-31; the test "
          "period is untouched. `+ @war_monitor` adds threat features from posts published before the forecast time "
          f"({len(wm_feats)} features: drone/missile/KAB post counts, drone counts written in posts, strategic aviation "
          "status, posts naming the oblast).\n"]
    v = dur[dur.time >= folds(test_start)[0][0]].y_dur_3h
    md += ["## 1. Why duration is hard\n",
           f"Durations in the validation weeks: median {v.median():.0f} min, middle half {v.quantile(.25):.0f}–{v.quantile(.75):.0f} min, "
           f"10% longer than {v.quantile(.9):.0f} min, 1% longer than {v.quantile(.99) / 60:.0f} h. A single number cannot "
           "describe this, so we predict a **range** (25th–75th percentile) and **bands**.\n"]
    t_q, t_b = duration_block(dur, BASE_FEATS, wm_feats, test_start)
    log("duration done")
    md += ["### Duration as a range (next alert starting within 3h)\n",
           "Pinball loss scores a percentile forecast (lower is better). A good 25–75% range should contain the "
           "true duration about 50% of the time; narrower is better at equal coverage.\n",
           "```\n" + t_q.round(3).to_string() + "\n```\n",
           f"### Duration bands ({', '.join(BAND_NAMES)})\n", "```\n" + t_b.round(3).to_string() + "\n```\n"]
    cnt = po[po.y_count_24h.notna()]
    t_c, t_h = count_hours_block(cnt, BASE_FEATS, wm_feats, test_start)
    log("24h done")
    md += ["## 2. Next 24 hours: number of alerts and hours under alert\n",
           "Skill = how much smaller the average error is than the 'daily average of the last 7 days' rule.\n",
           "Number of new alerts:\n", "```\n" + t_c.round(3).to_string() + "\n```\n",
           "Hours under alert:\n", "```\n" + t_h.round(3).to_string() + "\n```\n"]
    t_s = start_block(po[po.y_start_3h.notna()], BASE_FEATS, wm_feats, test_start)
    log("start done")
    md += ["## 3. Telegram check on a strong target: new alert within 3h\n", "```\n" + t_s.round(4).to_string() + "\n```\n"]
    (REP / "weak_targets.md").write_text("\n".join(md), encoding="utf-8")
    log("done")


if __name__ == "__main__":
    main()

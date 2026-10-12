"""Live forecast ("now" + week ahead) for the website (task 9). Models and settings are the frozen ones
(reports/final_choices.md, D47, D48); every model is retrained on all rows whose outcome is known before the
forecast moment t = the last hour of the pinned data.

Per raion and oblast:
  p1, p3     P(new alert within 1h / 3h)          tuned LightGBM (D47), history D40
  dur        typical duration [25th, 75th pct]     LightGBM quantile models (D41)
  cnt, hrs   next-24h alerts / hours [25th, 75th]  LightGBM quantile models (D49)
  week       P(new alert) in each of the next 56 Kyiv 3-hour blocks: blend model/pattern, w = 1 - lead/72h (D45)
  next24     the first 8 of those blocks
  red        share of red among the unit's alerts that started in the last 7 days (D35); if none, the national share
Also: coverage of the 24h ranges on the last validation week (6-12 Sep; the test weeks are not used, D49).

Also: history_pred_{level} = hourly 3h forecasts for the 7 days before t, from models trained before that week.

Usage: PYTHONPATH=.:scripts python scripts/predict_now.py
Output: reports/now_predictions.json
"""
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from build_panel import red_features
from compare_telegram import FIRST, training
from src.alerts.timing import TIMING_EXTRA, blend_timing, issue_times, timing_rows
from validate_models import BASE_FEATS, PARENT_FEATS, lgb_cls, lgb_reg

P, REP = Path("data/processed"), Path("reports")
TUNED = json.loads((REP / "tuning.json").read_text())
VAL_WEEK = (pd.Timestamp("2026-09-06", tz="UTC"), pd.Timestamp("2026-09-13", tz="UTC"))  # last validation week


def quant(tr, w, feats, y, X, n=200, alphas=(.25, .75)):
    return [lgb_reg(objective="quantile", alpha=a, n_estimators=n).fit(tr[feats], tr[y], sample_weight=w,
                                                                       categorical_feature=["oblast_code"]).predict(X[feats])
            for a in alphas]


def main():
    t0 = time.time()
    log = lambda m: print(f"[{time.time() - t0:6.0f}s] {m}", flush=True)
    araion = pd.read_parquet(P / "alerts_raion.parquet")
    data_until = max(araion.start.max(), araion.end.max())
    out, coverage = {}, {}
    for level in ("raion", "oblast"):
        pan = pd.read_parquet(P / f"panel_{level}.parquet")
        # forecast moment: the latest 00:00 / 12:00 Kyiv hour in the data (the timing model is trained on those issue
        # times); nothing after t is used. Targets are only known for windows ending before lk.
        t = issue_times(pan.time.max() - pd.Timedelta("2D"), pan.time.max())[-1]
        lk = t + pd.Timedelta("1h")
        start = t - pd.Timedelta("400D") if level == "raion" else FIRST
        df = pan[pan.time >= start].copy()
        df["oblast_code"] = df.oblast.astype("category")
        feats = BASE_FEATS + (PARENT_FEATS if level == "raion" else [])
        now = df[df.time == t].set_index("unit")
        res = pd.DataFrame(index=now.index)
        log(f"{level}: forecast moment {t}, {len(now)} units")

        for h in (1, 3):
            y = f"y_start_{h}h"
            tr, w = training(df[df[y].notna()], lk, h, level)
            m = lgb_cls(**TUNED[level]["params"]).fit(tr[feats], tr[y], sample_weight=w, categorical_feature=["oblast_code"])
            res[f"p{h}"] = m.predict_proba(now[feats])[:, 1]
            if h == 3:  # history strip: the 7 days before t, forecast by a model trained only on data before that week
                h0 = t - pd.Timedelta("168h")
                trh, wh = training(df[df[y].notna()], h0, h, level)
                mh = lgb_cls(**TUNED[level]["params"]).fit(trh[feats], trh[y], sample_weight=wh, categorical_feature=["oblast_code"])
                win = df[(df.time >= h0) & (df.time < t)]
                hp = pd.Series(mh.predict_proba(win[feats])[:, 1], index=[win.unit, win.time])
                grid = pd.date_range(h0, t - pd.Timedelta("1h"), freq="h")
                history_pred = {u: [round(float(hp.get((u, g), np.nan)), 3) for g in grid] for u in res.index}
        d = df[df.y_dur_3h.notna() & (df.y_dur_3h > 0)]
        tr, w = training(d, lk, 3 + 72, level)
        res["dur_lo"], res["dur_hi"] = quant(tr, w, feats, "y_dur_3h", now, n=300)
        d = df[df.y_count_24h.notna()]
        tr, w = training(d, lk, 24, level)
        res["cnt_lo"], res["cnt_hi"] = quant(tr, w, feats, "y_count_24h", now)
        res["hrs_lo"], res["hrs_hi"] = quant(tr, w, feats, "y_hours_24h", now)
        # coverage of the 24h ranges on the last validation week (models trained before it)
        trv, wv = training(d, VAL_WEEK[0], 24, level)
        va = d[(d.time >= VAL_WEEK[0]) & (d.time < VAL_WEEK[1])]
        coverage[level] = {}
        for y in ("y_count_24h", "y_hours_24h"):
            lo, hi = quant(trv, wv, feats, y, va)
            k = 0 if y == "y_count_24h" else 1  # same rounding as shown on the site
            lo, hi = np.round(np.minimum(lo, hi), k), np.round(np.maximum(lo, hi), k)
            coverage[level][y] = {"inside_25_75_range": float(np.mean((va[y] >= lo) & (va[y] <= hi))),
                                  "rows": int(len(va))}
        log(f"{level}: point targets done, coverage {coverage[level]}")

        # week ahead (D42/D45): timing rows for the issue time t
        hist_days, hl = (365, None) if level == "raion" else (730, 365)
        tf = [f for f in feats if f != "oblast_code"]
        tp = pan[pan.time >= t - pd.Timedelta(days=hist_days + 30)]
        parent = dict(zip(tp.unit, tp.oblast)) if level == "raion" else None
        iss = issue_times(tp.time.min() + pd.Timedelta("20D"), t)
        assert iss[-1] == t, f"forecast moment {t} is not a 00/12 Kyiv issue time"
        rows = timing_rows(tp, tf, iss, lk, parent_of=parent)
        rows["oblast_code"] = rows.unit.str.split("|").str[0].astype("category")
        X = tf + TIMING_EXTRA + (["parent_blk_rate14"] if level == "raion" else []) + ["oblast_code"]
        num = [c for c in X if c != "oblast_code"]
        rows[num] = rows[num].astype("float32")
        tr = rows[rows.y_block.notna() & (rows.block_start + pd.Timedelta("3h") <= lk) & (rows.issue_time >= t - pd.Timedelta(days=hist_days))]
        te = rows[rows.issue_time == t].sort_values(["unit", "lead_h"])
        w = None if hl is None else 0.5 ** ((lk - tr.issue_time).dt.total_seconds() / 86400 / hl)
        pm = lgb_cls(n_estimators=300).fit(tr[X], tr.y_block, sample_weight=w, categorical_feature=["oblast_code"]).predict_proba(te[X])[:, 1]
        te = te.assign(p=blend_timing(pm, te.blk_rate14.fillna(tr.y_block.mean()).values, te.lead_h.values))
        week = te.groupby("unit", sort=False).p.apply(list)
        blocks = sorted(te.block_start.unique())
        log(f"{level}: week ahead done ({len(blocks)} blocks from {pd.Timestamp(blocks[0])})")

        # red share (D35): unit's alerts that started in the last 7 days before t
        if level == "raion":
            ev = araion[araion.red.notna()].assign(unit=lambda a: a.oblast + "|" + a.raion).sort_values("start")
        else:
            ev = pd.read_parquet(P / "alerts_oblast.parquet").pipe(lambda a: a[a.red.notna()]).rename(columns={"oblast": "unit"}).sort_values("start")
        nat = ev[(ev.start < t) & (ev.start >= t - pd.Timedelta("7D"))].red.astype(float).mean()
        red = {u: red_features(ev, t, "unit", u)["unit_red_share_7d"] for u in res.index}

        out[level] = {}
        for u, r in res.iterrows():
            out[level][u] = {"p1": round(float(r.p1), 3), "p3": round(float(r.p3), 3),
                             "red": round(float(nat if pd.isna(red[u]) else red[u]), 3),
                             "dur": [int(max(1, round(min(r.dur_lo, r.dur_hi)))), int(max(1, round(max(r.dur_lo, r.dur_hi))))],
                             "cnt": [int(max(0, round(min(r.cnt_lo, r.cnt_hi)))), int(max(0, round(max(r.cnt_lo, r.cnt_hi))))],
                             "hrs": [round(float(np.clip(min(r.hrs_lo, r.hrs_hi), 0, 24)), 1), round(float(np.clip(max(r.hrs_lo, r.hrs_hi), 0, 24)), 1)],
                             "week": [round(float(x), 3) for x in week[u]]}
            out[level][u]["next24"] = out[level][u]["week"][:8]
        out["forecast_time_utc"] = t.isoformat()
        out[f"history_pred_{level}"] = history_pred
        out["block_starts_utc"] = [pd.Timestamp(b).tz_localize("UTC").isoformat() if pd.Timestamp(b).tzinfo is None
                                   else pd.Timestamp(b).isoformat() for b in blocks]
        del rows, tr, te
    out["data_until_utc"] = min(data_until, pd.Timestamp(out["forecast_time_utc"])).isoformat()  # nothing after t is used
    out["range_coverage_validation_week"] = coverage
    (REP / "now_predictions.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    log("done")


if __name__ == "__main__":
    main()

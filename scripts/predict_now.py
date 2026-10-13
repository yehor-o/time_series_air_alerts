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
  local      hromada/city alerts running at t inside the unit (D58): shown as notes, never as the unit's own alert
Also: coverage of the 24h ranges on the last validation week (6-12 Sep; the test weeks are not used, D49).

Also: history_pred_{level} = hourly 3h forecasts for the 7 days before t, from models trained before that week.

Modes (D51, D52):
  (default)  train everything and forecast at the latest 00/12 Kyiv hour (how the published 11/12 Oct forecasts were made)
  --train    train everything and save the models in models/ (gzipped LightGBM text files + models/meta.json);
             run twice a month (.github/workflows/retrain.yml)
  --predict  load the saved models and forecast at the LATEST hour of the data, no training (hourly live run).
             The week view comes from the latest 00:00/12:00 Kyiv issue time (the timing model's training setup);
             blocks that have already ended are dropped. history_pred_* is not produced (export_site keeps a rolling log).

Usage: PYTHONPATH=.:scripts python scripts/predict_now.py [--train | --predict]
Output: reports/now_predictions.json (default, --predict), models/ (--train)
"""
import argparse
import gzip
import json
import os
import time
from pathlib import Path

import lightgbm as lgb

import numpy as np
import pandas as pd

from build_panel import red_features
from compare_telegram import FIRST, training
from src.alerts.timing import TIMING_EXTRA, blend_timing, issue_times, timing_rows
from src.alerts.translit import hromada_en, hromada_uk
from validate_models import BASE_FEATS, NB_FEATS, NB_FEATS_RAION, PARENT_FEATS, lgb_cls, lgb_reg

P, REP = Path("data/processed"), Path("reports")
TUNED = json.loads((REP / "tuning.json").read_text())
VAL_WEEK = (pd.Timestamp("2026-09-06", tz="UTC"), pd.Timestamp("2026-09-13", tz="UTC"))  # last validation week
MOD = Path("models")
# Extra input groups kept after the validation comparison (reports/local_neighbours_ablation.md, D58/D55): a group is
# used only if it won there. Neighbours won at every target and level; local alerts (LOCAL_FEATS) did not (mixed for
# districts, worse for oblasts), so they stay out of the models and are shown on the site only. The saved models
# record their inputs in models/meta.json ("features").
EXTRA = {"raion": NB_FEATS_RAION, "oblast": NB_FEATS}


def model_feats(level, meta=None):
    if meta and "features" in meta:
        return meta["features"][level]
    return BASE_FEATS + (PARENT_FEATS if level == "raion" else []) + EXTRA[level]


def running_local(t, level):
    """Local alerts running at t (started before t, not ended by t), per unit."""
    loc = pd.read_parquet(P / "alerts_local.parquet")
    loc = loc[(loc.start < t) & (loc.end > t)].sort_values("start")
    unit = loc.oblast + "|" + loc.raion if level == "raion" else loc.oblast
    out = {}
    for u, r in zip(unit, loc.itertuples()):
        out.setdefault(u, []).append({"h": hromada_en(r.hromada), "h_uk": hromada_uk(r.hromada),
                                      "since": r.start.isoformat()})
    return out


def save_model(m, name):
    MOD.mkdir(exist_ok=True)
    with gzip.open(MOD / f"{name}.txt.gz", "wt", encoding="utf-8") as f:
        f.write(m.booster_.model_to_string())


def load_model(name):
    with gzip.open(MOD / f"{name}.txt.gz", "rt", encoding="utf-8") as f:
        return lgb.Booster(model_str=f.read())


def pred(m, X):
    """Probability (classifiers) or value (regressors), for fitted sklearn models and loaded boosters alike."""
    if hasattr(m, "predict_proba"):
        return m.predict_proba(X)[:, 1]
    return m.predict(X)


def quant_models(tr, w, feats, y, n=200, alphas=(.25, .75)):
    return [lgb_reg(objective="quantile", alpha=a, n_estimators=n).fit(tr[feats], tr[y], sample_weight=w, categorical_feature=["oblast_code"])
            for a in alphas]


def quant(tr, w, feats, y, X, n=200, alphas=(.25, .75)):
    return [m.predict(X[feats]) for m in quant_models(tr, w, feats, y, n, alphas)]


def main(mode="full"):
    """mode: full (train + forecast at the latest 00/12 Kyiv hour), train (save models), predict (saved models, latest hour)."""
    t0 = time.time()
    log = lambda m: print(f"[{time.time() - t0:6.0f}s] {m}", flush=True)
    araion = pd.read_parquet(P / "alerts_raion.parquet")
    data_until = max(araion.start.max(), araion.end.max())
    out, coverage = {}, {}
    meta = json.loads((MOD / "meta.json").read_text()) if mode == "predict" else {}
    for level in ("raion", "oblast"):
        pan = pd.read_parquet(P / f"panel_{level}.parquet")
        # issue time for training / the week view: the latest 00:00 / 12:00 Kyiv hour in the data (the timing model is
        # trained on those issue times). Live forecasts (predict) use the latest hour. Nothing after t is used.
        t_w = issue_times(pan.time.max() - pd.Timedelta("2D"), pan.time.max())[-1]
        t = pan.time.max() if mode == "predict" else t_w
        lk = t_w + pd.Timedelta("1h")  # training targets must be known before this
        start = (t - pd.Timedelta("400D") if level == "raion" else FIRST) if mode != "predict" else t - pd.Timedelta("2D")
        df = pan[pan.time >= start].copy()
        df["oblast_code"] = df.oblast.astype("category")
        feats = model_feats(level, meta if mode == "predict" else None)
        if mode != "predict":
            meta.setdefault("features", {})[level] = feats
        now = df[df.time == t].set_index("unit")
        res = pd.DataFrame(index=now.index)
        log(f"{level}: mode {mode}, forecast moment {t}, {len(now)} units")
        M = {}
        if mode == "predict":
            M = {k: load_model(f"{level}_{k}") for k in ("p1", "p3", "dur_lo", "dur_hi", "cnt_lo", "cnt_hi", "hrs_lo", "hrs_hi", "timing")}
        else:
            for h in (1, 3):
                y = f"y_start_{h}h"
                tr, w = training(df[df[y].notna()], lk, h, level)
                M[f"p{h}"] = lgb_cls(**TUNED[level]["params"]).fit(tr[feats], tr[y], sample_weight=w, categorical_feature=["oblast_code"])
                if h == 3 and mode == "full":  # history strip: the 7 days before t, from a model trained only on data before that week
                    h0 = t - pd.Timedelta("168h")
                    trh, wh = training(df[df[y].notna()], h0, h, level)
                    mh = lgb_cls(**TUNED[level]["params"]).fit(trh[feats], trh[y], sample_weight=wh, categorical_feature=["oblast_code"])
                    win = df[(df.time >= h0) & (df.time < t)]
                    hp = pd.Series(mh.predict_proba(win[feats])[:, 1], index=[win.unit, win.time])
                    grid = pd.date_range(h0, t - pd.Timedelta("1h"), freq="h")
                    out[f"history_pred_{level}"] = {u: [round(float(hp.get((u, g), np.nan)), 3) for g in grid] for u in res.index}
            d = df[df.y_dur_3h.notna() & (df.y_dur_3h > 0)]
            tr, w = training(d, lk, 3 + 72, level)
            M["dur_lo"], M["dur_hi"] = quant_models(tr, w, feats, "y_dur_3h", n=300)
            d = df[df.y_count_24h.notna()]
            tr, w = training(d, lk, 24, level)
            M["cnt_lo"], M["cnt_hi"] = quant_models(tr, w, feats, "y_count_24h")
            M["hrs_lo"], M["hrs_hi"] = quant_models(tr, w, feats, "y_hours_24h")
            # coverage of the 24h ranges on the last validation week (models trained before it)
            trv, wv = training(d, VAL_WEEK[0], 24, level)
            va = d[(d.time >= VAL_WEEK[0]) & (d.time < VAL_WEEK[1])]
            coverage[level] = {}
            for y in ("y_count_24h", "y_hours_24h"):
                lo, hi = quant(trv, wv, feats, y, va)
                k = 0 if y == "y_count_24h" else 1  # same rounding as shown on the site
                lo, hi = np.round(np.minimum(lo, hi), k), np.round(np.maximum(lo, hi), k)
                coverage[level][y] = {"inside_25_75_range": float(np.mean((va[y] >= lo) & (va[y] <= hi))), "rows": int(len(va))}
        for k in ("p1", "p3", "dur_lo", "dur_hi", "cnt_lo", "cnt_hi", "hrs_lo", "hrs_hi"):
            res[k] = pred(M[k], now[feats])
        log(f"{level}: point targets done")

        # week ahead (D42/D45): timing rows for the issue time t_w
        hist_days, hl = (365, None) if level == "raion" else (730, 365)
        # the timing model keeps the inputs it was validated with (D45); the new D58/D55 inputs are not validated for it
        tf = [f for f in BASE_FEATS + (PARENT_FEATS if level == "raion" else []) if f != "oblast_code"]
        tp = pan[pan.time >= t_w - pd.Timedelta(days=(45 if mode == "predict" else hist_days + 30))]
        parent = dict(zip(tp.unit, tp.oblast)) if level == "raion" else None
        iss = issue_times(tp.time.min() + pd.Timedelta("20D"), t_w)
        if mode == "predict":
            iss = iss[iss == t_w]
        assert iss[-1] == t_w, f"{t_w} is not a 00/12 Kyiv issue time"
        rows = timing_rows(tp, tf, iss, lk, parent_of=parent)
        rows["oblast_code"] = rows.unit.str.split("|").str[0].astype("category")
        X = tf + TIMING_EXTRA + (["parent_blk_rate14"] if level == "raion" else []) + ["oblast_code"]
        num = [c for c in X if c != "oblast_code"]
        rows[num] = rows[num].astype("float32")
        te = rows[rows.issue_time == t_w].sort_values(["unit", "lead_h"])
        if mode == "predict":
            prior = meta["timing_prior"][level]
        else:
            tr = rows[rows.y_block.notna() & (rows.block_start + pd.Timedelta("3h") <= lk) & (rows.issue_time >= t_w - pd.Timedelta(days=hist_days))]
            w = None if hl is None else 0.5 ** ((lk - tr.issue_time).dt.total_seconds() / 86400 / hl)
            M["timing"] = lgb_cls(n_estimators=300).fit(tr[X], tr.y_block, sample_weight=w, categorical_feature=["oblast_code"])
            prior = float(tr.y_block.mean())
            meta.setdefault("timing_prior", {})[level] = prior
        pm = pred(M["timing"], te[X])
        te = te.assign(p=blend_timing(pm, te.blk_rate14.fillna(prior).values, te.lead_h.values))
        te = te[te.block_start + pd.Timedelta("3h") > t]  # drop blocks that already ended (live runs between 00/12)
        week = te.groupby("unit", sort=False).p.apply(list)
        blocks = sorted(te.block_start.unique())
        log(f"{level}: week ahead done ({len(blocks)} blocks from {pd.Timestamp(blocks[0])})")
        if mode == "train":
            for k, m in M.items():
                save_model(m, f"{level}_{k}")
            log(f"{level}: models saved")

        # red share (D35): unit's alerts that started in the last 7 days before t
        if level == "raion":
            ev = araion[araion.red.notna()].assign(unit=lambda a: a.oblast + "|" + a.raion).sort_values("start")
        else:
            ev = pd.read_parquet(P / "alerts_oblast.parquet").pipe(lambda a: a[a.red.notna()]).rename(columns={"oblast": "unit"}).sort_values("start")
        nat = ev[(ev.start < t) & (ev.start >= t - pd.Timedelta("7D"))].red.astype(float).mean()
        red = {u: red_features(ev, t, "unit", u)["unit_red_share_7d"] for u in res.index}

        out[level] = {}
        loc_now = running_local(t, level)
        for u, r in res.iterrows():
            out[level][u] = {"p1": round(float(r.p1), 3), "p3": round(float(r.p3), 3), "active": int(now.at[u, "active"] > 0),
                             "red": round(float(nat if pd.isna(red[u]) else red[u]), 3),
                             "dur": [int(max(1, round(min(r.dur_lo, r.dur_hi)))), int(max(1, round(max(r.dur_lo, r.dur_hi))))],
                             "cnt": [int(max(0, round(min(r.cnt_lo, r.cnt_hi)))), int(max(0, round(max(r.cnt_lo, r.cnt_hi))))],
                             "hrs": [round(float(np.clip(min(r.hrs_lo, r.hrs_hi), 0, 24)), 1), round(float(np.clip(max(r.hrs_lo, r.hrs_hi), 0, 24)), 1)],
                             "week": [round(float(x), 3) for x in week[u]]}
            out[level][u]["next24"] = out[level][u]["week"][:8]
            if u in loc_now:
                out[level][u]["local"] = loc_now[u]
        out["forecast_time_utc"] = t.isoformat()
        out["week_time_utc"] = t_w.isoformat()
        out["block_starts_utc"] = [pd.Timestamp(b).tz_localize("UTC").isoformat() if pd.Timestamp(b).tzinfo is None
                                   else pd.Timestamp(b).isoformat() for b in blocks]
        del rows, te
    out["data_until_utc"] = min(data_until, pd.Timestamp(out["forecast_time_utc"])).isoformat()  # inputs use only data before t
    if mode == "predict":
        out["range_coverage_validation_week"] = meta["coverage"]
        out["models_trained_utc"] = meta["trained_utc"]
    else:
        out["range_coverage_validation_week"] = coverage
    if mode == "train":
        vf = Path(os.environ.get("VERSIONS_FILE", "data/versions.json"))  # which data versions the models were trained on
        versions = json.loads(vf.read_text()) if vf.exists() else {}
        meta.update({"trained_utc": out["forecast_time_utc"], "data_until_utc": out["data_until_utc"], "coverage": coverage,
                     "data_versions": versions})
        (MOD / "meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
        log(f"meta saved; models: {sum(f.stat().st_size for f in MOD.glob('*.txt.gz')) / 1e6:.1f} MB")
    else:
        (REP / "now_predictions.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    log("done")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--train", action="store_true")
    g.add_argument("--predict", action="store_true")
    a = ap.parse_args()
    main("train" if a.train else "predict" if a.predict else "full")

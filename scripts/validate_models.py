"""Validation of all models on walk-forward folds before the test period (Task 2, step 3-5).

The test period (the last 28 days) is NOT used here: every row with time >= TEST_START is dropped
before anything else happens. For each weekly fold, models train only on rows whose target window
ended before the fold started ("purge"), and predict that week. This mimics real forecasting.

Targets (D23, D24) and models
  start 1h / 3h      baselines (same-hour rate, persistence), logistic regression, LightGBM
  duration 1h / 3h   baseline (median of the unit's last 10 alerts), LightGBM on log-duration
  24h count / hours  baseline (last 24h repeats), LightGBM (Poisson / L2)
  24h timing blocks  baseline (same block yesterday), LightGBM
  red | alert        baselines (previous alert's level, unit red share 7d), logistic, LightGBM
                     -> own split, reform period only (D24/D28)

Usage: PYTHONPATH=. python scripts/validate_models.py
Outputs: reports/validation.md, reports/validation_metrics.json
"""
import json
import os
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

P, REP = Path("data/processed"), Path("reports")
SEED = 42
N_FOLDS, FOLD = 4, pd.Timedelta("7D")
# Fixed test period (D31, D50): starts 2026-09-13; the pinned data ended 2026-10-11 10:00 UTC. Kept fixed so that newer
# data (refreshes of the live forecast) can never shift the validation folds or the reported test scores.
TEST_START = pd.Timestamp("2026-09-13", tz="UTC")
TEST_END = pd.Timestamp("2026-10-11 10:00", tz="UTC")
WINDOWS = {"all (since 2024-01)": None, "12 months": pd.Timedelta("365D"), "6 months": pd.Timedelta("182D"),
           "3 months": pd.Timedelta("91D")}
BASE_FEATS = ["active", "h_since_start", "h_since_end", "med_dur10", "starts_1h", "starts_3h", "starts_6h",
              "starts_24h", "starts_168h", "alert_h_3h", "alert_h_24h", "alert_h_168h", "hod_rate7", "hod_rate14",
              "night_rate14", "day_rate14", "nat_active_share", "nat_starts_1h", "nat_starts_3h", "nat_starts_24h",
              "hour", "dow", "oblast_code"]
PARENT_FEATS = ["parent_active_share", "parent_starts_1h", "parent_starts_3h", "parent_starts_24h"]
LOCAL_FEATS = ["local_active_n", "local_new_active_n", "local_starts_1h", "local_starts_3h", "local_starts_24h"]  # D58
NB_FEATS = ["nb_active_share", "nb_starts_1h", "nb_starts_3h", "nb_starts_24h", "nb_max_starts_24h"]  # D55
NB_FEATS_RAION = NB_FEATS + ["nb_other_oblast_active_share"]
if os.environ.get("QUICK"):  # smoke test: one fold, one window, few raions
    N_FOLDS, WINDOWS = 1, {"all (since 2024-01)": None}
LOG_FEATS = ["h_since_start", "h_since_end", "med_dur10", "starts_24h", "starts_168h", "alert_h_24h",
             "alert_h_168h", "nat_starts_1h", "nat_starts_3h", "nat_starts_24h", "parent_starts_24h"]
LGB_CLS = dict(n_estimators=400, learning_rate=0.05, num_leaves=63, min_child_samples=500, subsample=0.7,
               subsample_freq=1, colsample_bytree=0.8, random_state=SEED, verbose=-1)


def lgb_cls(**kw):
    return lgb.LGBMClassifier(**{**LGB_CLS, **kw})


def lgb_reg(**kw):
    return lgb.LGBMRegressor(**{**LGB_CLS, **kw})


def logreg():
    return make_pipeline(StandardScaler(), LogisticRegression(max_iter=300, C=1.0))


def lr_matrix(df, feats):
    """Inputs for logistic regression: log of skewed counts, hour/weekday as sine/cosine."""
    X = df[[f for f in feats if f not in ("hour", "dow", "oblast_code")]].copy()
    for c in LOG_FEATS:
        if c in X:
            X[c] = np.log1p(X[c])
    X["hour_sin"], X["hour_cos"] = np.sin(2 * np.pi * df.hour / 24), np.cos(2 * np.pi * df.hour / 24)
    X["dow_sin"], X["dow_cos"] = np.sin(2 * np.pi * df.dow / 7), np.cos(2 * np.pi * df.dow / 7)
    return X.fillna(X.median())


def cls_scores(y, p, base=None):
    p = np.clip(np.asarray(p, float), 1e-4, 1 - 1e-4)
    out = {"Brier": brier_score_loss(y, p), "log-loss": log_loss(y, p, labels=[0, 1]),
           "ROC-AUC": roc_auc_score(y, p) if len(set(y)) > 1 else np.nan,
           "PR-AUC": average_precision_score(y, p) if len(set(y)) > 1 else np.nan}
    if base is not None:
        out["skill vs same-hour"] = 1 - out["Brier"] / brier_score_loss(y, np.clip(base, 1e-4, 1 - 1e-4))
    return out


def reg_scores(y, p):
    e = np.abs(np.asarray(y) - np.asarray(p))
    return {"MAE": e.mean(), "median abs error": np.median(e), "RMSE": np.sqrt((e ** 2).mean())}


def folds(test_start):
    return [(test_start - (N_FOLDS - i) * FOLD, test_start - (N_FOLDS - i - 1) * FOLD) for i in range(N_FOLDS)]


def split(df, lo, hi, purge_h, window=None, first=None):
    tr = df[df.time < lo - pd.Timedelta(hours=purge_h)]
    if window is not None:
        tr = tr[tr.time >= lo - window]
    if first is not None:
        tr = tr[tr.time >= first]
    return tr, df[(df.time >= lo) & (df.time < hi)]


def mean_table(rows):
    return pd.DataFrame(rows).groupby("model", sort=False).mean(numeric_only=True)


def run_start(df, feats, h, test_start, first, log):
    """Start-of-alert classifiers; also chooses the training window on the folds."""
    y = f"y_start_{h}h"
    d = df[df[y].notna()]
    res, window_res, oof = [], [], []
    for lo, hi in folds(test_start):
        tr, va = split(d, lo, hi, h, first=first)
        base = va.hod_rate14.values
        # persistence: P(y | a start happened in the last h hours), estimated on train
        pers = tr.groupby(tr[f"starts_{h}h"] > 0)[y].mean()
        res.append({"model": "baseline: same hour, last 14 days", **cls_scores(va[y], base, base)})
        res.append({"model": "baseline: persistence", **cls_scores(va[y], (va[f"starts_{h}h"] > 0).map(pers).values, base)})
        m = logreg().fit(lr_matrix(tr, feats), tr[y])
        res.append({"model": "logistic regression", **cls_scores(va[y], m.predict_proba(lr_matrix(va, feats))[:, 1], base)})
        for wname, w in WINDOWS.items():
            trw, _ = split(d, lo, hi, h, window=w, first=first)
            g = lgb_cls().fit(trw[feats], trw[y], categorical_feature=["oblast_code"])
            p = g.predict_proba(va[feats])[:, 1]
            window_res.append({"model": f"LightGBM, train {wname}", **cls_scores(va[y], p, base)})
            if wname == "all (since 2024-01)":
                res.append({"model": "LightGBM", **cls_scores(va[y], p, base)})
                oof.append(va[["time", "hour", y]].assign(p=p))
        log(f"  start {h}h fold {lo:%m-%d} done")
    oof = pd.concat(oof)
    night = (oof.hour >= 22) | (oof.hour < 6)
    dn = {"day (06-22 Kyiv)": cls_scores(oof[y][~night], oof.p[~night]),
          "night (22-06 Kyiv)": cls_scores(oof[y][night], oof.p[night])}
    cal = oof.assign(bin=pd.cut(oof.p, [0, .05, .1, .2, .3, .4, .5, .6, .7, .8, .9, 1], include_lowest=True)) \
        .groupby("bin", observed=True).agg(rows=("p", "size"), predicted=("p", "mean"), observed=(y, "mean"))
    return mean_table(res), mean_table(window_res), pd.DataFrame(dn).T, cal, g, feats


def run_duration(df, feats, h, test_start, first):
    y = f"y_dur_{h}h"
    d = df[df[y].notna() & (df[y] > 0)]
    res = []
    for lo, hi in folds(test_start):
        tr, va = split(d, lo, hi, h + 72, first=first)  # long alerts: purge 3 extra days
        base = va.med_dur10.fillna(tr[y].median())
        res.append({"model": "baseline: median of last 10 alerts", **reg_scores(va[y], base)})
        g = lgb_reg(objective="l2").fit(tr[feats], np.log(tr[y]), categorical_feature=["oblast_code"])
        res.append({"model": "LightGBM (log minutes)", **reg_scores(va[y], np.exp(g.predict(va[feats])))})
    return mean_table(res)


def run_24h(df, feats, test_start, first):
    out = {}
    res_c, res_h, res_b = [], [], []
    d = df[df.y_count_24h.notna()].copy()
    d = d.sort_values(["unit", "time"])
    for b in range(4):  # baseline: did block b happen yesterday? (known at t: that window ended <= t)
        d[f"yday_block{b}"] = d.groupby("unit")[f"y_block{b}_24h"].shift(24)
    for lo, hi in folds(test_start):
        tr, va = split(d, lo, hi, 24, first=first)
        res_c.append({"model": "baseline: same as last 24h", **reg_scores(va.y_count_24h, va.starts_24h)})
        g = lgb_reg(objective="poisson").fit(tr[feats], tr.y_count_24h, categorical_feature=["oblast_code"])
        res_c.append({"model": "LightGBM (Poisson)", **reg_scores(va.y_count_24h, g.predict(va[feats]))})
        res_h.append({"model": "baseline: same as last 24h", **reg_scores(va.y_hours_24h, va.alert_h_24h)})
        g = lgb_reg(objective="l2").fit(tr[feats], tr.y_hours_24h, categorical_feature=["oblast_code"])
        res_h.append({"model": "LightGBM", **reg_scores(va.y_hours_24h, np.clip(g.predict(va[feats]), 0, 24))})
        for b in range(4):
            yb = f"y_block{b}_24h"
            rate = tr.groupby(tr[f"yday_block{b}"].fillna(0) > 0)[yb].mean()
            pb = (va[f"yday_block{b}"].fillna(0) > 0).map(rate).values
            res_b.append({"model": f"block +{6*b}..{6*b+6}h baseline: yesterday", **cls_scores(va[yb], pb)})
            g = lgb_cls().fit(tr[feats], tr[yb], categorical_feature=["oblast_code"])
            res_b.append({"model": f"block +{6*b}..{6*b+6}h LightGBM", **cls_scores(va[yb], g.predict_proba(va[feats])[:, 1])})
    out["count"], out["hours"], out["timing"] = mean_table(res_c), mean_table(res_h), mean_table(res_b)
    return out


def run_red(ev, feats):
    """Yellow/red, reform period only (D28): folds = the weeks of Sep 13-19 and Sep 20-26; test = Sep 27+ (unused)."""
    red_feats = ["prev_red", "unit_red_share_7d", "parent_red_share_24h", "nat_red_share_3h", "nat_red_share_24h",
                 "nat_red_count_3h", "nat_red_count_24h"] + feats
    f = [pd.Timestamp(x, tz="UTC") for x in ("2026-09-13", "2026-09-20", "2026-09-27")]
    res = []
    for lo, hi in zip(f[:-1], f[1:]):
        tr, va = ev[ev.time < lo], ev[(ev.time >= lo) & (ev.time < hi)]
        prior = tr.y_red.mean()
        pr = tr.groupby(tr.prev_red.fillna(-1)).y_red.mean()
        res.append({"model": "baseline: overall red share", **cls_scores(va.y_red, np.full(len(va), prior))})
        res.append({"model": "baseline: previous alert's level", **cls_scores(va.y_red, va.prev_red.fillna(-1).map(pr).fillna(prior).values)})
        res.append({"model": "baseline: raion red share last 7 days", **cls_scores(va.y_red, va.unit_red_share_7d.fillna(prior).values)})
        m = logreg().fit(lr_matrix(tr, red_feats), tr.y_red)
        res.append({"model": "logistic regression", **cls_scores(va.y_red, m.predict_proba(lr_matrix(va, red_feats))[:, 1])})
        g = lgb_cls(n_estimators=200, min_child_samples=50, num_leaves=15).fit(tr[red_feats], tr.y_red, categorical_feature=["oblast_code"])
        res.append({"model": "LightGBM", **cls_scores(va.y_red, g.predict_proba(va[red_feats])[:, 1])})
    return mean_table(res), {"train events (fold 2)": int((ev.time < f[1]).sum()), "validation events": int(((ev.time >= f[0]) & (ev.time < f[2])).sum())}


def fmt(df, digits=3):
    return "```\n" + df.round(digits).to_string() + "\n```\n"


def main():
    t0 = time.time()
    log = lambda m: print(f"[{time.time() - t0:6.0f}s] {m}", flush=True)
    pr = pd.read_parquet(P / "panel_raion.parquet")
    po = pd.read_parquet(P / "panel_oblast.parquet")
    ev = pd.read_parquet(P / "red_events.parquet")
    last = max(pr.time.max(), po.time.max()) + pd.Timedelta("1h")
    test_start = TEST_START
    codes = {o: i for i, o in enumerate(sorted(po.oblast.unique()))}
    first = pd.Timestamp("2024-01-31", tz="UTC")  # 30 days of warm-up for the "rate" features
    for d in (pr, po, ev):
        d["oblast_code"] = d.oblast.map(codes).astype("category")
    pr, po = pr[pr.time < test_start], po[po.time < test_start]  # the test period is never touched here
    if os.environ.get("QUICK"):
        pr = pr[pr.unit.isin(pr.unit.unique()[:12])]
    ev_val = ev[ev.time < pd.Timestamp("2026-09-27", tz="UTC")]
    log(f"test period starts {test_start} (not used); folds: {[f'{a:%m-%d}' for a, _ in folds(test_start)]}")

    feats_r, feats_o = BASE_FEATS + PARENT_FEATS, BASE_FEATS
    R = {"meta": {"test_start": str(test_start), "folds": [[str(a), str(b)] for a, b in folds(test_start)]}}
    md = ["# Validation results\n",
          f"Walk-forward validation on {N_FOLDS} weekly folds before the test period "
          f"(folds start {', '.join(f'{a:%Y-%m-%d}' for a, _ in folds(test_start))}; the test period from "
          f"{test_start:%Y-%m-%d} is untouched). Numbers are averages over the folds. Data: "
          f"{pr.unit.nunique()} raions and {po.unit.nunique()} oblasts, issue time = every hour.\n",
          "How to read: **Brier** = mean squared error of the probabilities (lower is better); **skill** = how much "
          "smaller the Brier is than the 'same hour, last 14 days' rule (0 = no better, 0.3 = 30% smaller); "
          "**ROC-AUC** = chance that a random hour with a new alert gets a higher probability than a random hour "
          "without one (0.5 = coin flip); **PR-AUC** = how precise the top-ranked hours are (compare with the base "
          "rate); **MAE** = average absolute error in the target's units.\n"]
    for name, df, feats in (("raion", pr, feats_r), ("oblast", po, feats_o)):
        for h in (1, 3):
            log(f"{name} start {h}h")
            main_t, win_t, dn, cal, model, f = run_start(df, feats, h, test_start, first, log)
            imp = pd.Series(model.booster_.feature_importance("gain"), index=f).sort_values(ascending=False)
            imp = (imp / imp.sum()).head(10)
            R[f"{name}_start_{h}h"] = {"models": main_t.to_dict("index"), "windows": win_t.to_dict("index"),
                                       "day_night": dn.to_dict("index"), "importance": imp.to_dict()}
            md += [f"## {name.title()}: will a new alert start within {h}h?\n",
                   f"Base rate (share of hours with a new alert): {df[f'y_start_{h}h'].loc[df.time >= folds(test_start)[0][0]].mean():.3f}\n",
                   fmt(main_t), "Training window (LightGBM):\n", fmt(win_t), "Day vs night (LightGBM):\n", fmt(dn),
                   "Calibration (LightGBM): when the model says p, how often did an alert actually start?\n", fmt(cal),
                   "Most important inputs (share of total gain, last fold):\n", fmt(imp.to_frame("gain share")), ""]
        for h in (1, 3):
            log(f"{name} duration {h}h")
            t = run_duration(df, feats, h, test_start, first)
            R[f"{name}_duration_{h}h"] = t.to_dict("index")
            md += [f"## {name.title()}: how long will the next alert (starting within {h}h) last? (minutes)\n", fmt(t, 1)]
        log(f"{name} 24h")
        o = run_24h(df, feats, test_start, first)
        for k, t in o.items():
            R[f"{name}_24h_{k}"] = t.to_dict("index")
        md += [f"## {name.title()}: next 24 hours\n", "Number of new alerts:\n", fmt(o["count"], 2),
               "Hours under alert:\n", fmt(o["hours"], 2),
               "Timing: will an alert start in each 6-hour block of the next 24h?\n", fmt(o["timing"])]
    log("red")
    t, info = run_red(ev_val, feats_r)
    R["red_given_alert"] = {"models": t.to_dict("index"), **info}
    md += ["## Yellow/red: if an alert starts in a raion, is it red? (reform period only)\n",
           f"Folds: train from 2026-09-06, validate on the weeks of Sep 13–19 and Sep 20–26 "
           f"({info['validation events']} alerts). Red share overall: {ev_val.y_red.mean():.2f}. "
           "Thin data: about 3 weeks of training at most.\n", fmt(t)]
    name = "validation_quick" if os.environ.get("QUICK") else "validation"
    (REP / f"{name}.md").write_text("\n".join(md), encoding="utf-8")
    (REP / f"{name}_metrics.json").write_text(json.dumps(R, indent=1, default=float))
    log("done")


if __name__ == "__main__":
    main()

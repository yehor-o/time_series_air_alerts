"""FINAL TEST RUN (task 8; choices frozen in reports/final_choices.md, signed off by the user 2026-10-12).

The test period (2026-09-13 00:00 UTC -> end of data) is scored ONCE. Every model is trained once on rows whose
target window ended before the test start (purge), with the frozen settings:
  start 1h / 3h      LightGBM, tuned settings (D47); history D40 (raion last 12 months; oblast full history,
                     recency half-life 12 months). Compared with: same-hour rule, persistence, logistic regression,
                     and the same LightGBM + @war_monitor / + @kpszsu (pre-registered comparison for the site).
  duration range     LightGBM quantiles 25/50/75 (D41) vs the unit's last 10 alerts.
  24h count / hours  LightGBM (Poisson / L1) vs "same as last 24h" and "7-day daily average".
  week timing        blend of LightGBM timing model and pattern rule, w = 1 - lead/72h (D45).
  red | alert        raion red share last 7 days (D35); own split: train Sep 6-26, test Sep 27+ (D32).

Usage: PYTHONPATH=.:scripts python scripts/final_test.py
Outputs: reports/test_results.md, reports/test_metrics.json, reports/test_predictions_{raion,oblast}.parquet,
         reports/test_red_predictions.parquet
"""
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from compare_kpszsu import kpszsu_features
from compare_telegram import FIRST, training
from explore_weak_targets import pinball, recent_duration_quantiles
from src.alerts.telegram import load_channel
from src.alerts.telegram_features import add_war_monitor, war_monitor_features
from src.alerts.timing import TIMING_EXTRA, blend_timing, issue_times, timing_rows
from validate_models import BASE_FEATS, PARENT_FEATS, cls_scores, lgb_cls, lgb_reg, logreg, lr_matrix, reg_scores

P, REP = Path("data/processed"), Path("reports")
TUNED = json.loads((REP / "tuning.json").read_text())  # D47
BINS = [0, .05, .1, .2, .3, .4, .5, .6, .7, .8, .9, 1]


def fmt(df, digits=3):
    return "```\n" + df.round(digits).to_string() + "\n```\n"


def lr_fit_predict(tr, te, feats, y):
    """Logistic regression; missing values filled with TRAINING medians (no test statistics)."""
    cols = [f for f in feats if f not in ("hour", "dow", "oblast_code")]
    te = te.copy()
    te[cols] = te[cols].fillna(tr[cols].median())
    return logreg().fit(lr_matrix(tr, feats), tr[y]).predict_proba(lr_matrix(te, feats))[:, 1]


def per_week(te, y, p, test_start):
    wk = ((te.time - test_start) // pd.Timedelta("7D")).astype(int) + 1
    return pd.DataFrame({f"week {w}": cls_scores(te[y][wk == w], p[wk == w], te.hod_rate14.values[wk == w])
                         for w in sorted(wk.unique())}).T[["Brier", "ROC-AUC", "skill vs same-hour"]]


def main():
    t0 = time.time()
    log = lambda m: print(f"[{time.time() - t0:6.0f}s] {m}", flush=True)
    wm = load_channel("data/raw/telegram/war_monitor.jsonl")
    kp = load_channel("data/raw/telegram/kpszsu/part*.jsonl")
    M = {}
    md = ["# Final test results (scored once)\n"]
    for level in ("raion", "oblast"):
        pan = pd.read_parquet(P / f"panel_{level}.parquet")
        last_known = pan.time.max() + pd.Timedelta("1h")
        test_start = (last_known - pd.Timedelta("28D")).floor("D")
        start = test_start - pd.Timedelta("400D") if level == "raion" else FIRST
        df = pan[pan.time >= start].copy()
        df["oblast_code"] = df.oblast.astype("category")
        feats = BASE_FEATS + (PARENT_FEATS if level == "raion" else [])
        params = TUNED[level]["params"]
        grid = pd.DatetimeIndex(sorted(df.time.unique()))
        oblasts = sorted(df.oblast.unique())
        n1, r1 = war_monitor_features(wm, grid, oblasts)
        n2, r2 = kpszsu_features(kp, grid, oblasts)
        df = add_war_monitor(add_war_monitor(df, n1, r1), n2, r2)
        wm_f, kp_f = list(n1.columns) + list(r1.columns), list(n2.columns) + list(r2.columns)
        te_all = df[df.time >= test_start]
        if level == "raion":
            md.insert(1, f"Test period: **{test_start:%Y-%m-%d %H:%M} UTC → {last_known:%Y-%m-%d %H:%M} UTC** "
                         f"({(last_known - test_start) / pd.Timedelta('1D'):.1f} days). Models trained once on data "
                         "before the test start; nothing in the test period was used for any choice. Pinned data: "
                         "Vadimkin `bf0c323c`, JustJimer `7abc556b`.\n")
        log(f"{level}: {len(df):,} rows, test rows {len(te_all):,}")
        md.append(f"## {level.title()} ({df.unit.nunique()} units)\n")
        M[level] = {}
        preds = te_all[["time", "unit", "oblast", "y_start_1h", "y_start_3h", "y_dur_3h", "y_count_24h", "y_hours_24h"]].copy()

        # ---- new alert within 1h / 3h
        for h in (1, 3):
            y = f"y_start_{h}h"
            d = df[df[y].notna()]
            tr, w = training(d, test_start, h, level)
            te = d[d.time >= test_start]
            base = te.hod_rate14.values
            pers = tr.groupby(tr[f"starts_{h}h"] > 0)[y].mean()
            res = {"baseline: same hour, last 14 days": base,
                   "baseline: persistence": (te[f"starts_{h}h"] > 0).map(pers).values,
                   "logistic regression": lr_fit_predict(tr, te, feats, y)}
            fit = lambda f: lgb_cls(**params).fit(tr[f], tr[y], sample_weight=w, categorical_feature=["oblast_code"])
            main_model = fit(feats)
            res["LightGBM (chosen)"] = main_model.predict_proba(te[feats])[:, 1]
            res["LightGBM + @war_monitor"] = fit(feats + wm_f).predict_proba(te[feats + wm_f])[:, 1]
            res["LightGBM + @kpszsu"] = fit(feats + kp_f).predict_proba(te[feats + kp_f])[:, 1]
            tab = pd.DataFrame({k: cls_scores(te[y], v, base) for k, v in res.items()}).T
            p = res["LightGBM (chosen)"]
            night = ((te.hour >= 22) | (te.hour < 6)).values
            dn = pd.DataFrame({"day (06-22 Kyiv)": cls_scores(te[y][~night], p[~night], base[~night]),
                               "night (22-06 Kyiv)": cls_scores(te[y][night], p[night], base[night])}).T
            cal = pd.DataFrame({"p": p, "y": te[y].values}).assign(bin=lambda x: pd.cut(x.p, BINS, include_lowest=True)) \
                .groupby("bin", observed=True).agg(rows=("p", "size"), predicted=("p", "mean"), observed=("y", "mean"))
            wk = per_week(te, y, p, test_start)
            md += [f"### New alert within {h}h\n", f"Base rate: {te[y].mean():.3f} ({len(te):,} unit-hours).\n", fmt(tab, 4),
                   "Chosen model by time of day:\n", fmt(dn), "Chosen model by test week:\n", fmt(wk),
                   "Calibration (chosen model):\n", fmt(cal)]
            M[level][f"start_{h}h"] = {"table": tab.round(5).to_dict("index"), "day_night": dn.round(5).to_dict("index"),
                                       "weeks": wk.round(5).to_dict("index"), "calibration": cal.reset_index().astype({"bin": str}).round(4).to_dict("records"),
                                       "base_rate": float(te[y].mean()), "rows": int(len(te))}
            preds[f"p_start_{h}h"] = main_model.predict_proba(te_all[feats])[:, 1]
            log(f"{level} start {h}h done")
            (REP / "test_results.md").write_text("\n".join(md), encoding="utf-8")

        # ---- duration range (next alert starting within 3h)
        alerts = pd.read_parquet(P / f"alerts_{level}.parquet")
        alerts["unit"] = alerts.oblast + "|" + alerts.raion if level == "raion" else alerts.oblast
        d = df[df.y_dur_3h.notna() & (df.y_dur_3h > 0)].copy()
        d = d.join(recent_duration_quantiles(alerts, d))
        tr, w = training(d, test_start, 3 + 72, level)
        te = d[d.time >= test_start]
        yv, yt = te.y_dur_3h.values, tr.y_dur_3h.values
        q = {"baseline: last 10 alerts": {"q25": te.q25_last10.fillna(np.quantile(yt, .25)).values,
                                          "q50": te.med_dur10.fillna(np.median(yt)).values,
                                          "q75": te.q75_last10.fillna(np.quantile(yt, .75)).values}}
        q["LightGBM quantiles (chosen)"] = {f"q{int(a * 100)}": lgb_reg(objective="quantile", alpha=a, n_estimators=300)
                                            .fit(tr[feats], yt, sample_weight=w, categorical_feature=["oblast_code"]).predict(te[feats])
                                            for a in (.25, .5, .75)}
        rows = {}
        for k, v in q.items():
            lo_, hi_ = np.minimum(v["q25"], v["q75"]), np.maximum(v["q25"], v["q75"])
            rows[k] = {"median abs error of the middle value (min)": np.median(np.abs(yv - v["q50"])),
                       "pinball loss": np.mean([pinball(yv, v[n], a) for n, a in (("q25", .25), ("q50", .5), ("q75", .75))]),
                       "true duration inside the 25-75% range": np.mean((yv >= lo_) & (yv <= hi_)),
                       "average range width (min)": np.mean(hi_ - lo_)}
        tab = pd.DataFrame(rows).T
        md += ["### Duration of the next alert (starting within 3h), as a range\n",
               f"{len(te):,} test cases; true durations: median {np.median(yv):.0f} min, middle half "
               f"{np.quantile(yv, .25):.0f}–{np.quantile(yv, .75):.0f} min. Ideal coverage of a 25–75% range: 50%.\n", fmt(tab)]
        M[level]["duration"] = tab.round(4).to_dict("index")
        log(f"{level} duration done")

        # ---- next 24h: number of alerts, hours under alert
        d = df[df.y_count_24h.notna()]
        tr, w = training(d, test_start, 24, level)
        te = d[d.time >= test_start]
        c = lgb_reg(objective="poisson", n_estimators=200).fit(tr[feats], tr.y_count_24h, sample_weight=w, categorical_feature=["oblast_code"])
        hh = lgb_reg(objective="l1", n_estimators=200).fit(tr[feats], tr.y_hours_24h, sample_weight=w, categorical_feature=["oblast_code"])
        out = {}
        for tgt, pm, b1, b7 in (("count", c.predict(te[feats]), te.starts_24h, te.starts_168h / 7),
                                ("hours", np.clip(hh.predict(te[feats]), 0, 24), te.alert_h_24h, te.alert_h_168h / 7)):
            yv = te[f"y_{tgt}_24h"]
            t = pd.DataFrame({"baseline: same as last 24h": reg_scores(yv, b1), "baseline: daily average of last 7 days": reg_scores(yv, b7),
                              "LightGBM (chosen)": reg_scores(yv, pm)}).T
            t["skill vs 7-day average"] = 1 - t.MAE / t.MAE.loc["baseline: daily average of last 7 days"]
            out[tgt] = t
        preds["p_count_24h"] = c.predict(te_all[feats])
        preds["p_hours_24h"] = np.clip(hh.predict(te_all[feats]), 0, 24)
        md += ["### Next 24 hours\n", f"Number of new alerts (true average {te.y_count_24h.mean():.2f}):\n", fmt(out["count"]),
               f"Hours under alert (true average {te.y_hours_24h.mean():.2f} h):\n", fmt(out["hours"])]
        M[level]["next24h"] = {k: v.round(4).to_dict("index") for k, v in out.items()}
        preds.to_parquet(REP / f"test_predictions_{level}.parquet", index=False)
        log(f"{level} 24h done")
        (REP / "test_results.md").write_text("\n".join(md), encoding="utf-8")

        # ---- week-ahead timing (D42/D45)
        hist_days, hl = (365, None) if level == "raion" else (730, 365)
        tfeats = [f for f in feats if f != "oblast_code"]
        tp = pan[pan.time >= test_start - pd.Timedelta(days=hist_days + 30)]
        parent = dict(zip(tp.unit, tp.oblast)) if level == "raion" else None
        iss = issue_times(tp.time.min() + pd.Timedelta("20D"), last_known - pd.Timedelta("1h"))
        rows = timing_rows(tp, tfeats, iss, last_known, parent_of=parent)
        rows["oblast_code"] = rows.unit.str.split("|").str[0].astype("category")
        X = tfeats + TIMING_EXTRA + (["parent_blk_rate14"] if level == "raion" else []) + ["oblast_code"]
        num = [x for x in X if x != "oblast_code"]
        rows[num] = rows[num].astype("float32")
        rows = rows[rows.y_block.notna()]
        tr = rows[(rows.block_start + pd.Timedelta("3h") <= test_start) & (rows.issue_time >= test_start - pd.Timedelta(days=hist_days))]
        te = rows[rows.issue_time >= test_start]
        w = None if hl is None else 0.5 ** ((test_start - tr.issue_time).dt.total_seconds() / 86400 / hl)
        pm = lgb_cls(n_estimators=300).fit(tr[X], tr.y_block, sample_weight=w, categorical_feature=["oblast_code"]).predict_proba(te[X])[:, 1]
        pat = te.blk_rate14.fillna(tr.y_block.mean()).values
        pb = blend_timing(pm, pat, te.lead_h.values)
        day = (te.lead_h.values // 24).astype(int) + 1
        v = {"pattern rule": pat, "timing model alone": pm, "blend (chosen)": pb}
        allb = pd.DataFrame({k: cls_scores(te.y_block, p, pat) for k, p in v.items()}).T.rename(columns={"skill vs same-hour": "skill vs pattern"})
        byd = {k: {f"day {dd}": cls_scores(te.y_block[day == dd], p[day == dd], pat[day == dd])["ROC-AUC"]
                   for dd in range(1, 8) if (day == dd).sum() and te.y_block[day == dd].nunique() > 1} for k, p in v.items()}
        byb = {k: {f"day {dd}": cls_scores(te.y_block[day == dd], p[day == dd])["Brier"]
                   for dd in range(1, 8) if (day == dd).sum() and te.y_block[day == dd].nunique() > 1} for k, p in v.items()}
        md += ["### When: new alert in each 3-hour Kyiv block of the next 7 days\n",
               f"Forecasts issued at 00:00 and 12:00 Kyiv inside the test period; {len(te):,} (unit, issue, block) cases "
               "whose block ended before the end of data (later days of the week have fewer cases).\n",
               "All blocks:\n", fmt(allb, 4), "ROC-AUC by lead day:\n", fmt(pd.DataFrame(byd).T),
               "Brier by lead day:\n", fmt(pd.DataFrame(byb).T, 4)]
        M[level]["timing"] = {"all": allb.round(5).to_dict("index"), "auc_by_day": byd, "brier_by_day": byb}
        del rows, tr, te
        log(f"{level} timing done")
        (REP / "test_results.md").write_text("\n".join(md), encoding="utf-8")

    # ---- red vs yellow (raion alerts, own split D32)
    ev = pd.read_parquet(P / "red_events.parquet")
    ev["oblast_code"] = ev.oblast.astype("category")
    cut = pd.Timestamp("2026-09-27", tz="UTC")
    tr, te = ev[ev.time < cut], ev[ev.time >= cut]
    prior = tr.y_red.mean()
    pr = tr.groupby(tr.prev_red.fillna(-1)).y_red.mean()
    lvl = ["prev_red", "unit_red_share_7d", "parent_red_share_24h", "nat_red_share_3h", "nat_red_share_24h"]
    res = {"baseline: overall red share": np.full(len(te), prior),
           "baseline: previous alert's level": te.prev_red.fillna(-1).map(pr).fillna(prior).values,
           "raion red share last 7 days (chosen)": te.unit_red_share_7d.fillna(prior).values,
           "logistic, 5 level features": lr_fit_predict(tr, te, lvl, "y_red")}
    tab = pd.DataFrame({k: cls_scores(te.y_red, v) for k, v in res.items()}).T
    md += ["## Red vs yellow (if an alert starts in a raion)\n",
           f"Own split (D32): trained on {len(tr):,} alerts from 6–26 Sep, tested on {len(te):,} alerts from 27 Sep "
           f"to the end of data. Red share in the test alerts: {te.y_red.mean():.2f}.\n", fmt(tab, 4)]
    M["red"] = {"table": tab.round(5).to_dict("index"), "train": int(len(tr)), "test": int(len(te)), "red_share": float(te.y_red.mean())}
    te.assign(p_red=res["raion red share last 7 days (chosen)"])[["time", "unit", "oblast", "red", "y_red", "p_red"]] \
        .to_parquet(REP / "test_red_predictions.parquet", index=False)
    (REP / "test_results.md").write_text("\n".join(md), encoding="utf-8")
    (REP / "test_metrics.json").write_text(json.dumps(M, indent=1, default=float), encoding="utf-8")
    log("done")


if __name__ == "__main__":
    main()

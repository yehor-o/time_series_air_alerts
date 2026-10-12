"""LightGBM tuning for the new-alert classifiers (plan approved by the user, 2026-10-12).

Search on "new alert within 3h", confirm on 1h. Same 4 weekly validation folds as validate_models.py
(Aug 16 – Sep 12 2026; the test period is untouched), same training history (D40: raion last 12 months,
oblast full history with recency weights), same inputs, fixed seed.

Candidates: the current settings + 11 combinations drawn (seed 0) from a small grid fixed in advance.
Adoption rule (fixed before running): a candidate replaces the current settings only if it
  - has lower Brier than the current settings in at least 3 of the 4 weeks, and
  - lowers the average Brier by at least 0.5%, and
  - is not worse than the current settings on the 1h target (average Brier).
Among qualifying candidates the lowest average 3h Brier wins. Decided separately for raion and oblast.

Usage: PYTHONPATH=.:scripts python scripts/tune_lgbm.py
Output: reports/tuning.md, reports/tuning.json
"""
import itertools
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from compare_telegram import FIRST, training
from validate_models import BASE_FEATS, LGB_CLS, PARENT_FEATS, cls_scores, folds, lgb_cls

P, REP = Path("data/processed"), Path("reports")
GRID = {"num_leaves": [31, 63, 127], "min_child_samples": [200, 500, 1000],
        "lr_trees": [(0.05, 400), (0.03, 700)], "colsample_bytree": [0.6, 0.8], "reg_lambda": [0.0, 1.0]}
DEFAULT = {"num_leaves": 63, "min_child_samples": 500, "lr_trees": (0.05, 400), "colsample_bytree": 0.8, "reg_lambda": 0.0}
N_RANDOM = 11


def candidates():
    combos = [dict(zip(GRID, v)) for v in itertools.product(*GRID.values())]
    combos = [c for c in combos if c != DEFAULT]
    pick = np.random.default_rng(0).choice(len(combos), N_RANDOM, replace=False)
    return [DEFAULT] + [combos[i] for i in sorted(pick)]


def params(c):
    lr, n = c["lr_trees"]
    return {"num_leaves": c["num_leaves"], "min_child_samples": c["min_child_samples"], "learning_rate": lr,
            "n_estimators": n, "colsample_bytree": c["colsample_bytree"], "reg_lambda": c["reg_lambda"]}


def label(c):
    lr, n = c["lr_trees"]
    return (f"leaves {c['num_leaves']}, min rows {c['min_child_samples']}, lr {lr} x {n}, "
            f"cols {c['colsample_bytree']}, lambda {c['reg_lambda']}")


def run(df, feats, level, y, h, cands, test_start, log):
    d = df[df[y].notna()]
    out = []
    for lo, hi in folds(test_start):
        tr, w = training(d, lo, h, level)
        va = d[(d.time >= lo) & (d.time < hi)]
        for k, c in enumerate(cands):
            p = lgb_cls(**params(c)).fit(tr[feats], tr[y], sample_weight=w,
                                        categorical_feature=["oblast_code"]).predict_proba(va[feats])[:, 1]
            out.append({"cand": k, "fold": f"{lo:%m-%d}", **cls_scores(va[y], p, va.hod_rate14.values)})
        log(f"{level} {h}h fold {lo:%m-%d}")
    return pd.DataFrame(out)


def main():
    t0 = time.time()
    log = lambda m: print(f"[{time.time() - t0:6.0f}s] {m}", flush=True)
    cands = candidates()
    md = ["# LightGBM tuning (validation only)\n",
          "Search on 'new alert within 3h', confirmed on 1h. 4 weekly validation folds (Aug 16 – Sep 12 2026); the test "
          "period is untouched. Same inputs and training history as before (D40); only the LightGBM settings change. "
          f"Current settings = candidate 0 ({label(DEFAULT)}; subsample 0.7, seed {LGB_CLS['random_state']}).\n",
          "**Adoption rule (fixed before running):** lower Brier than candidate 0 in at least 3 of 4 weeks, at least "
          "0.5% lower average Brier, and not worse on the 1h target.\n",
          "Candidates:\n", "\n".join(f"- {k}: {label(c)}" for k, c in enumerate(cands)) + "\n"]
    result = {"candidates": [params(c) for c in cands]}
    for level in ("raion", "oblast"):
        df = pd.read_parquet(P / f"panel_{level}.parquet")
        last = df.time.max() + pd.Timedelta("1h")
        test_start = (last - pd.Timedelta("28D")).floor("D")
        start = folds(test_start)[0][0] - pd.Timedelta("400D") if level == "raion" else FIRST
        df = df[(df.time >= start) & (df.time < test_start)].copy()
        df["oblast_code"] = df.oblast.astype("category")
        feats = BASE_FEATS + (PARENT_FEATS if level == "raion" else [])
        r3 = run(df, feats, level, "y_start_3h", 3, cands, test_start, log)
        piv = r3.pivot(index="cand", columns="fold", values="Brier")
        mean = r3.groupby("cand")[["Brier", "log-loss", "ROC-AUC", "skill vs same-hour"]].mean()
        mean["weeks better than current"] = (piv.lt(piv.loc[0], axis=1)).sum(axis=1)
        mean["Brier change vs current"] = mean.Brier / mean.Brier.loc[0] - 1
        ok = mean[(mean["weeks better than current"] >= 3) & (mean["Brier change vs current"] <= -0.005)]
        best = int(ok.Brier.idxmin()) if len(ok) else 0
        md += [f"## {level.title()}\n", "New alert within 3h (average of 4 weeks):\n",
               "```\n" + mean.round(4).to_string() + "\n```\n",
               "Brier per week:\n", "```\n" + piv.round(4).to_string() + "\n```\n"]
        check = None
        if best:
            r1 = run(df, feats, level, "y_start_1h", 1, [cands[0], cands[best]], test_start, log)
            m1 = r1.groupby("cand")[["Brier", "log-loss", "ROC-AUC", "skill vs same-hour"]].mean()
            m1.index = ["current (0)", f"candidate {best}"]
            md += ["1h check:\n", "```\n" + m1.round(4).to_string() + "\n```\n"]
            check = bool(m1.Brier.iloc[1] <= m1.Brier.iloc[0])
            if not check:
                best = 0
        verdict = (f"**Adopt candidate {best}** ({label(cands[best])})." if best else
                   "**Keep the current settings**: no candidate passed the adoption rule.")
        md.append(f"Verdict for {level}: {verdict}\n")
        result[level] = {"chosen": best, "params": params(cands[best]), "passed_3h": [int(i) for i in ok.index],
                         "one_hour_check": check}
        (REP / "tuning.md").write_text("\n".join(md), encoding="utf-8")
        (REP / "tuning.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    log("done")


if __name__ == "__main__":
    main()

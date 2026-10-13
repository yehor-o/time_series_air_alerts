"""With vs without the new inputs: local (hromada/city) alerts (D58) and neighbouring districts (D55).

Same 4 validation weeks as all earlier comparisons (Aug 16 – Sep 12 2026; the test period from Sep 13 is untouched),
the accepted training history (D40) and the tuned LightGBM (D47). Data: the D58/D59 tables (raion alerts = raion-wide
alerts only; official-feed outage masked; stuck alerts fixed). Four arms that differ only in their inputs:
  base         the inputs of the current models
  + local      + local_* (hromada/city alerts inside the unit)
  + neighbours + nb_* (units sharing a border)
  + both
Rule (as for Telegram, D44): an input group is kept only if it wins on these weeks.

Usage: PYTHONPATH=.:scripts python scripts/compare_local_neighbours.py
Output: reports/local_neighbours_ablation.md, reports/local_neighbours_ablation.json
"""
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from compare_telegram import FIRST, training
from validate_models import (BASE_FEATS, LOCAL_FEATS, NB_FEATS, NB_FEATS_RAION, PARENT_FEATS, TEST_START, cls_scores,
                             folds, lgb_cls, lgb_reg, mean_table)

P, REP = Path("data/processed"), Path("reports")
TUNED = json.loads((REP / "tuning.json").read_text())
WATCH = ["Харківська область|Харківський район", "Дніпропетровська область|Нікопольський район",
         "Кіровоградська область|Олександрійський район", "Харківська область", "Дніпропетровська область"]


def arms(level):
    base = BASE_FEATS + (PARENT_FEATS if level == "raion" else [])
    nb = NB_FEATS_RAION if level == "raion" else NB_FEATS
    return {"base": base, "+ local": base + LOCAL_FEATS, "+ neighbours": base + nb, "+ both": base + LOCAL_FEATS + nb}


def main():
    t0 = time.time()
    log = lambda m: print(f"[{time.time() - t0:6.0f}s] {m}", flush=True)
    md = ["# New inputs: local (hromada/city) alerts and neighbouring districts\n",
          "Same model (tuned LightGBM, D47), same training history (D40), same 4 validation weeks (Aug 16 – Sep 12 "
          "2026; the test period from Sep 13 is untouched). All arms use the corrected data (D58: a hromada/city alert is "
          "not an alert of the whole district; D59: official-feed outage of Aug 29 – Sep 2 masked, stuck alerts fixed). "
          "The arms differ only in their inputs.\n",
          "**skill** = how much smaller the Brier score is than the 'same hour, last 14 days' rule (higher is better); "
          "**ROC-AUC**: 0.5 = coin flip, 1 = perfect ranking; **MAE** = average error (lower is better).\n"]
    R = {}
    for level in ("raion", "oblast"):
        cols = None
        df = pd.read_parquet(P / f"panel_{level}.parquet")
        start = folds(TEST_START)[0][0] - pd.Timedelta("400D") if level == "raion" else FIRST
        df = df[(df.time >= start) & (df.time < TEST_START)].copy()
        df["oblast_code"] = df.oblast.astype("category")
        A = arms(level)
        params = TUNED[level]["params"]
        log(f"{level}: {len(df):,} rows")
        md.append(f"## {level.title()}\n")
        R[level] = {}
        for h in (1, 3):
            y, rows, per_unit = f"y_start_{h}h", [], []
            d = df[df[y].notna()]
            for lo, hi in folds(TEST_START):
                tr, w = training(d, lo, h, level)
                va = d[(d.time >= lo) & (d.time < hi)]
                for name, f in A.items():
                    m = lgb_cls(**params).fit(tr[f], tr[y], sample_weight=w, categorical_feature=["oblast_code"])
                    p = m.predict_proba(va[f])[:, 1]
                    rows.append({"model": name, **cls_scores(va[y], p, va.hod_rate14.values)})
                    per_unit.append(va[["unit", y]].assign(p=p, arm=name, base=va.hod_rate14.values))
                log(f"{level} {h}h fold {lo:%m-%d}")
            t = mean_table(rows)
            R[level][f"start_{h}h"] = t.to_dict("index")
            md += [f"New alert within {h}h:\n", "```\n" + t.round(4).to_string() + "\n```\n"]
            pu = pd.concat(per_unit)
            pu = pu[pu.unit.isin(WATCH)]
            if len(pu):
                br = pu.assign(se=(pu.p - pu[y]) ** 2).groupby(["unit", "arm"]).se.mean().unstack()[list(A)]
                md += [f"Brier score for the most affected units, {h}h (lower is better):\n",
                       "```\n" + br.round(4).to_string() + "\n```\n"]
            (REP / "local_neighbours_ablation.md").write_text("\n".join(md), encoding="utf-8")
        rows = []
        d = df[df.y_count_24h.notna()]
        for lo, hi in folds(TEST_START):
            tr, w = training(d, lo, 24, level)
            va = d[(d.time >= lo) & (d.time < hi)]
            for name, f in A.items():
                c = lgb_reg(objective="poisson", n_estimators=200).fit(tr[f], tr.y_count_24h, sample_weight=w,
                                                                       categorical_feature=["oblast_code"]).predict(va[f])
                hh = lgb_reg(objective="l1", n_estimators=200).fit(tr[f], tr.y_hours_24h, sample_weight=w,
                                                                   categorical_feature=["oblast_code"]).predict(va[f])
                rows.append({"model": name, "count MAE": np.mean(np.abs(va.y_count_24h - c)),
                             "hours MAE": np.mean(np.abs(va.y_hours_24h - np.clip(hh, 0, 24)))})
            log(f"{level} 24h fold {lo:%m-%d}")
        t = mean_table(rows)
        R[level]["24h"] = t.to_dict("index")
        md += ["Next 24h, number of alerts and hours under alert (average error):\n", "```\n" + t.round(3).to_string() + "\n```\n"]
        (REP / "local_neighbours_ablation.md").write_text("\n".join(md), encoding="utf-8")
        (REP / "local_neighbours_ablation.json").write_text(json.dumps(R, indent=1, default=float))
    log("done")


if __name__ == "__main__":
    main()

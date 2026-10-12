"""D45 variants: how should the week-ahead view combine the timing model and the pattern rule?

Same data, folds, training rows and LightGBM settings as validate_timing.py (last 2 validation weeks; the
test period is untouched). Variants, scored on all 56 blocks and per lead day:
  pattern       share of the last 14 days with a new alert in this clock block (blk_rate14)
  full          LightGBM timing model with all inputs (incl. "alerts running now")
  calendar      LightGBM with NO current-state inputs: clock block, weekday, lead, pattern shares and 14-day habits
  hybrid A      full for blocks starting < 48 h ahead, pattern after
  hybrid B      full for < 48 h, calendar after
  blend         w * full + (1 - w) * calendar, w = max(0, 1 - lead_h / 72)  (fixed schedule, nothing tuned)
  blend/pattern w * full + (1 - w) * pattern, same w

Usage: PYTHONPATH=.:scripts python scripts/validate_timing_variants.py
Output: reports/timing_variants.md
"""
import time
from pathlib import Path

import numpy as np
import pandas as pd

from src.alerts.timing import TIMING_EXTRA, issue_times, timing_rows
from validate_models import BASE_FEATS, PARENT_FEATS, cls_scores, folds, lgb_cls, TEST_START

P, REP = Path("data/processed"), Path("reports")
HABITS = ["hod_rate7", "hod_rate14", "night_rate14", "day_rate14"]  # 14-day habits, not "state right now"


def main():
    t0 = time.time()
    log = lambda m: print(f"[{time.time() - t0:6.0f}s] {m}", flush=True)
    md = ["# Timing model: how to combine model and pattern (D45 variants, validation)\n",
          "Last 2 validation weeks (Aug 30 – Sep 12 2026); the test period is untouched. Lower Brier is better; "
          "skill = Brier improvement over the pattern rule (negative = worse than the pattern).\n"]
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
        par = ["parent_blk_rate14"] if level == "raion" else []
        X_full = feats + TIMING_EXTRA + par + ["oblast_code"]
        X_cal = HABITS + TIMING_EXTRA + par + ["oblast_code"]
        num = [c for c in X_full if c != "oblast_code"]
        rows[num] = rows[num].astype("float32")
        rows = rows[rows.y_block.notna()]
        log(f"{level}: {len(rows):,} timing rows")
        out = []
        for lo, hi in fl:
            tr = rows[(rows.block_start + pd.Timedelta("3h") <= lo) & (rows.issue_time >= lo - pd.Timedelta(days=hist_days))]
            va = rows[(rows.issue_time >= lo) & (rows.issue_time < hi)]
            w = None if hl is None else 0.5 ** ((lo - tr.issue_time).dt.total_seconds() / 86400 / hl)
            fit = lambda X: lgb_cls(n_estimators=300).fit(tr[X], tr.y_block, sample_weight=w, categorical_feature=["oblast_code"])
            pf = fit(X_full).predict_proba(va[X_full])[:, 1]
            pc = fit(X_cal).predict_proba(va[X_cal])[:, 1]
            pat = va.blk_rate14.fillna(tr.y_block.mean()).values
            lead = va.lead_h.values
            wt = np.clip(1 - lead / 72, 0, 1)
            near = lead < 48
            v = {"pattern": pat, "full model": pf, "calendar-only model": pc,
                 "hybrid A (full <48h, pattern after)": np.where(near, pf, pat),
                 "hybrid B (full <48h, calendar after)": np.where(near, pf, pc),
                 "blend full/calendar (w=1-lead/72h)": wt * pf + (1 - wt) * pc,
                 "blend full/pattern (w=1-lead/72h)": wt * pf + (1 - wt) * pat}
            day = (lead // 24).astype(int) + 1
            for name, p in v.items():
                s = cls_scores(va.y_block, p, pat)
                out.append({"variant": name, "day": "all", **s})
                for d in range(1, 8):
                    m = day == d
                    if m.sum() and len(set(va.y_block[m])) > 1:
                        out.append({"variant": name, "day": f"day {d}", **cls_scores(va.y_block[m], p[m], pat[m])})
            log(f"{level} fold {lo:%m-%d}")
        df = pd.DataFrame(out).groupby(["variant", "day"], sort=False).mean().reset_index()
        order = list(dict.fromkeys(df.variant))
        allb = df[df.day == "all"].set_index("variant").loc[order][["Brier", "log-loss", "ROC-AUC", "skill vs same-hour"]]
        allb = allb.rename(columns={"skill vs same-hour": "skill vs pattern"})
        bd = df[df.day != "all"].pivot(index="variant", columns="day", values="Brier").loc[order]
        ad = df[df.day != "all"].pivot(index="variant", columns="day", values="ROC-AUC").loc[order]
        md += [f"## {level.title()}\n", "All 56 blocks:\n", "```\n" + allb.round(4).to_string() + "\n```\n",
               "Brier by lead day (day 1 = next 24 h):\n", "```\n" + bd.round(4).to_string() + "\n```\n",
               "ROC-AUC by lead day:\n", "```\n" + ad.round(3).to_string() + "\n```\n"]
        (REP / "timing_variants.md").write_text("\n".join(md), encoding="utf-8")
        del rows
    log("done")


if __name__ == "__main__":
    main()

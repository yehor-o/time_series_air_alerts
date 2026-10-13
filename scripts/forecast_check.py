"""Forecast check (site page "Forecast check"): saved forecasts vs what actually happened.

1. Archive: every published 00:00 / 12:00 Kyiv forecast is saved once as site/data/archive/<YYYY-MM-DDTHH>Z.json (the next-24h part:
   p1, p3, the 8 Kyiv 3-hour blocks, count and hours ranges), from reports/now_predictions.json.
   --from-git <commit> also archives an older published forecast from the site files in that git commit.
2. Check: for every archived forecast, the actual outcome from the current data, with the same definitions the models
   were scored on (panel targets): new alert started in each 3-hour block, number of new alerts and hours under alert
   in the next 24 h. Outcomes not known yet (after the end of the data) are null.
   Writes site/data/check.json.

Usage: PYTHONPATH=. python scripts/forecast_check.py [--from-git <commit>]
"""
import argparse
import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

P, REP, ARC = Path("data/processed"), Path("reports"), Path("site/data/archive")
FEATURED = ["м. Київ|м. Київ", "Харківська область|Харківський район", "Львівська область|Львівський район"]
KEEP = ("p1", "p3", "cnt", "hrs", "next24")


def snapshot(t, blocks, raion, oblast, models_trained=None):
    return {"forecast_time_utc": t, "block_starts_utc": blocks[:8], "models_trained_utc": models_trained,
            "raion": {u: {k: v[k] for k in KEEP} for u, v in raion.items()},
            "oblast": {u: {k: v[k] for k in KEEP} for u, v in oblast.items()}}


def save(snap):
    ARC.mkdir(parents=True, exist_ok=True)
    f = ARC / (pd.Timestamp(snap["forecast_time_utc"]).strftime("%Y-%m-%dT%H") + "Z.json")
    if not f.exists():  # a published forecast is never overwritten
        f.write_text(json.dumps(snap, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print("archived", f)


def from_git(commit):
    show = lambda p: json.loads(subprocess.run(["git", "show", f"{commit}:{p}"], capture_output=True, text=True, check=True).stdout)
    meta, now, week = show("site/data/meta.json"), show("site/data/now.json"), show("site/data/week.json")
    assert not meta.get("sample"), "that commit has sample data"
    return snapshot(meta["forecast_time_utc"], week["block_starts_utc"], now["raion"], now["oblast"])


def main(git_commit=None):
    if git_commit:
        save(from_git(git_commit))
    now = json.loads((REP / "now_predictions.json").read_text())
    if pd.Timestamp(now["forecast_time_utc"]).tz_convert("Europe/Kyiv").hour in (0, 12):  # archive the 00:00 / 12:00 Kyiv forecasts only
        save(snapshot(now["forecast_time_utc"], now["block_starts_utc"], now["raion"], now["oblast"], now.get("models_trained_utc")))

    pan = {lv: pd.read_parquet(P / f"panel_{lv}.parquet", columns=["time", "unit", "y_start_1h", "y_count_24h", "y_hours_24h"])
           for lv in ("raion", "oblast")}
    alerts = {"raion": pd.read_parquet(P / "alerts_raion.parquet").assign(unit=lambda a: a.oblast + "|" + a.raion),
              "oblast": pd.read_parquet(P / "alerts_oblast.parquet").assign(unit=lambda a: a.oblast)}
    data_end = pan["raion"].time.max() + pd.Timedelta("1h")
    out = {"data_until_utc": data_end.isoformat(), "featured": FEATURED, "snapshots": []}
    for f in sorted(ARC.glob("*Z.json"), reverse=True):
        s = json.loads(f.read_text())
        t = pd.Timestamp(s["forecast_time_utc"])
        bst = [pd.Timestamp(b) for b in s["block_starts_utc"]]
        # snapshots saved before 13 Oct 2026 carry no model date: they come from the deadline models (before the D58 data fix)
        res = {"forecast_time_utc": s["forecast_time_utc"], "block_starts_utc": s["block_starts_utc"],
               "models_trained_utc": s.get("models_trained_utc"),
               "known_until_utc": min(data_end, t + pd.Timedelta("24h")).isoformat()}
        for lv in ("raion", "oblast"):
            pv = pan[lv][(pan[lv].time >= t) & (pan[lv].time < t + pd.Timedelta("24h"))]
            y1 = pv.pivot(index="time", columns="unit", values="y_start_1h")
            at_t = pan[lv][pan[lv].time == t].set_index("unit")
            a = alerts[lv]
            a = a[(a.start < min(data_end, t + pd.Timedelta("24h"))) & (a.end.isna() | (a.end > t))]
            units, ys, ps = {}, [], []
            for u, fc in s[lv].items():
                blocks = []
                for b in bst:
                    hrs = [b + pd.Timedelta(hours=k) for k in range(3)]
                    v = [y1.at[h, u] if (h in y1.index and u in y1.columns) else np.nan for h in hrs]
                    blocks.append(None if any(pd.isna(x) for x in v) else int(max(v) > 0))
                for p, y in zip(fc["next24"], blocks):
                    if y is not None:
                        ys.append(y); ps.append(p)
                cnt = at_t.y_count_24h.get(u, np.nan) if len(at_t) else np.nan
                hh = at_t.y_hours_24h.get(u, np.nan) if len(at_t) else np.nan
                g = a[a.unit == u]
                al = [[round((max(st, t) - t) / pd.Timedelta("1min")), round((min(e if pd.notna(e) else data_end, data_end, t + pd.Timedelta("24h")) - t) / pd.Timedelta("1min")),
                       "unknown" if pd.isna(r) else ("red" if r else "yellow")] for st, e, r in zip(g.start, g.end, g.red)]
                units[u] = {**fc, "actual_blocks": blocks, "actual_cnt": None if pd.isna(cnt) else int(cnt),
                            "actual_hrs": None if pd.isna(hh) else round(float(hh), 1), "alerts": al}
            done = [v for v in units.values() if v["actual_cnt"] is not None]
            summ = {"blocks_known": len(ys), "blocks_with_alert": int(sum(ys)),
                    "auc": float(roc_auc_score(ys, ps)) if len(set(ys)) > 1 else None,
                    "brier": float(np.mean((np.array(ps) - np.array(ys)) ** 2)) if ys else None,
                    "avg_forecast_alert_blocks": float(np.mean([p for p, y in zip(ps, ys) if y])) if sum(ys) else None,
                    "avg_forecast_quiet_blocks": float(np.mean([p for p, y in zip(ps, ys) if not y])) if len(ys) > sum(ys) else None,
                    "units_complete": len(done),
                    "count_inside_range": float(np.mean([v["cnt"][0] <= v["actual_cnt"] <= v["cnt"][1] for v in done])) if done else None,
                    "hours_inside_range": float(np.mean([v["hrs"][0] <= v["actual_hrs"] <= v["hrs"][1] for v in done])) if done else None}
            res[lv] = units
            res[f"summary_{lv}"] = summ
            print(f.name, lv, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in summ.items()})
        out["snapshots"].append(res)
    Path("site/data/check.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"check.json {Path('site/data/check.json').stat().st_size / 1e3:.0f} kB")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-git")
    main(ap.parse_args().from_git)

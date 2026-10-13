"""Export the real data for the website (task 10): site/data/{meta,now,week,history,replay,metrics}.json
in the format of scripts/make_sample_site_data.py, with "sample": false.

Inputs: reports/now_predictions.json (scripts/predict_now.py), reports/test_predictions_{raion,oblast}.parquet and
reports/test_metrics.json (scripts/final_test.py), data/processed/alerts_*.parquet, site/data/raions.geojson.
  history  the 7 days before the forecast moment: actual alerts (with yellow/red level) and the hourly 3h forecast
           of a model trained only on data before that week (predict_now.py), so genuine out-of-sample forecasts
  replay   the test weeks hour by hour: 3h forecast (%) and whether a new alert started (null = unknown)
  metrics  test results (headline, calibration, day/night, Telegram) + the full test tables for the comparison page

Usage: PYTHONPATH=. python scripts/export_site.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

P, REP, OUT = Path("data/processed"), Path("reports"), Path("site/data")


def dump(name, obj):
    obj["sample"] = False
    (OUT / f"{name}.json").write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{name}.json {(OUT / f'{name}.json').stat().st_size / 1e3:.0f} kB")


def level_name(red):
    return "unknown" if pd.isna(red) else ("red" if red else "yellow")


def main():
    now = json.loads((REP / "now_predictions.json").read_text())
    PREV = {n: json.loads((OUT / f"{n}.json").read_text()) for n in ("meta", "now") if (OUT / f"{n}.json").exists()}
    M = json.loads((REP / "test_metrics.json").read_text())
    shapes = json.loads((OUT / "raions.geojson").read_text())["features"]
    units = [f["properties"] for f in shapes if f["properties"]["status"] == "forecast"]
    oblasts = sorted({u["oblast_id"] for u in units})
    ob_name = {u["oblast_id"]: u["oblast"] for u in units}
    t = pd.Timestamp(now["forecast_time_utc"])
    missing = [u["id"] for u in units if u["id"] not in now["raion"]] + [o for o in oblasts if o not in now["oblast"]]
    assert not missing, f"units without a forecast: {missing}"

    dump("meta", {"title": "Time-Series Air Alert Forecast, Ukraine (demo)", "forecast_time_utc": now["forecast_time_utc"],
                  "data_until_utc": now["data_until_utc"], "week_time_utc": now.get("week_time_utc", now["forecast_time_utc"]),
                  "models_trained_utc": now.get("models_trained_utc"),
                  "units": {"raion": {u["id"]: {"name": u["name"], "oblast": u["oblast"], "oblast_id": u["oblast_id"]} for u in units},
                            "oblast": {o: {"name": ob_name[o]} for o in oblasts}}})
    keep = ("p1", "p3", "red", "dur", "cnt", "hrs", "next24", "active", "local")
    dump("now", {lv: {u: {k: v[k] for k in keep if k in v} for u, v in now[lv].items()} for lv in ("raion", "oblast")})
    dump("week", {"block_starts_utc": now["block_starts_utc"],
                  **{lv: {u: v["week"] for u, v in now[lv].items()} for lv in ("raion", "oblast")}})

    # history: 168 h before the forecast moment. Forecast values come from (1) predict_now's out-of-sample history model
    # (default mode), else (2) the rolling log of the site's own hourly forecasts (p3_log.json, live runs), else (3) the
    # previous history.json, so the strip only ever shows forecasts made before each hour.
    h0, hours = t - pd.Timedelta("168h"), 168
    hist = {"start_utc": h0.isoformat(), "hours": hours}
    prev = json.loads((OUT / "history.json").read_text()) if (OUT / "history.json").exists() else {}
    prev = {} if prev.get("sample", True) else prev
    plog = json.loads((OUT / "p3_log.json").read_text()) if (OUT / "p3_log.json").exists() else {"raion": {}, "oblast": {}}
    old = (PREV["meta"], PREV["now"]) if len(PREV) == 2 else None  # the previously published forecast joins the log too
    for lv in ("raion", "oblast"):  # this forecast joins the log; keep 8 days
        if old and not old[1].get("sample", True):
            plog[lv].setdefault(pd.Timestamp(old[0]["forecast_time_utc"]).isoformat(), {u: v["p3"] for u, v in old[1][lv].items()})
        plog[lv][t.isoformat()] = {u: v["p3"] for u, v in now[lv].items()}
        plog[lv] = {k: v for k, v in plog[lv].items() if pd.Timestamp(k) >= t - pd.Timedelta("192h")}
    hgrid = pd.date_range(h0, t - pd.Timedelta("1h"), freq="h")

    def hour_preds(lv, u):
        if f"history_pred_{lv}" in now:
            return now[f"history_pred_{lv}"][u]
        p0 = pd.Timestamp(prev["start_utc"]) if prev else None
        vals = []
        for g in hgrid:
            v = plog[lv].get(g.isoformat(), {}).get(u)
            if v is None and prev and u in prev.get(lv, {}):
                k = int((g - p0) / pd.Timedelta("1h"))
                v = prev[lv][u]["pred"][k] / 100 if 0 <= k < len(prev[lv][u]["pred"]) else None
            vals.append(np.nan if v is None else v)
        return vals
    replay = {"horizon_h": 3}
    for lv in ("raion", "oblast"):
        a = pd.read_parquet(P / f"alerts_{lv}.parquet")
        a["unit"] = a.oblast + "|" + a.raion if lv == "raion" else a.oblast
        a = a[(a.start < t) & (a.end.isna() | (a.end > h0))]
        tp = pd.read_parquet(REP / f"test_predictions_{lv}.parquet")
        ids = [u["id"] for u in units] if lv == "raion" else oblasts
        hist[lv] = {}
        for u in ids:
            g = a[a.unit == u]
            al = [[int(max(0, (s - h0) / pd.Timedelta("1min"))),
                   int(min(hours * 60, ((e if pd.notna(e) and e < t else t) - h0) / pd.Timedelta("1min"))), level_name(r)]
                  for s, e, r in zip(g.start, g.end, g.red)]
            hist[lv][u] = {"alerts": al, "pred": [int(round(100 * x)) if pd.notna(x) else 0 for x in hour_preds(lv, u)]}
        # replay: the test weeks, hour by hour
        grid = pd.date_range(tp.time.min(), tp.time.max(), freq="h")
        pp = tp.pivot(index="time", columns="unit", values="p_start_3h").reindex(grid)
        yy = tp.pivot(index="time", columns="unit", values="y_start_3h").reindex(grid)
        known = yy.notna().mean(axis=1) > 0.5  # drop the last hours whose 3h outcome is not known yet
        grid = grid[: int(np.flatnonzero(known.values)[-1]) + 1]
        replay.update({"start_utc": grid[0].isoformat(), "hours": len(grid)})
        replay[lv] = {u: {"p": [int(round(100 * x)) for x in pp[u].loc[grid]],
                          "y": [None if pd.isna(x) else int(x) for x in yy[u].loc[grid]]} for u in ids}
    dump("history", hist)
    (OUT / "p3_log.json").write_text(json.dumps(plog, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    dump("replay", replay)

    # metrics
    cal = pd.read_parquet(REP / "test_predictions_raion.parquet")
    cal = cal[cal.y_start_3h.notna()]
    b = np.minimum((cal.p_start_3h * 10).astype(int), 9)
    calib = [{"bin": f"{i * 10}-{i * 10 + 10}%", "predicted": float(cal.p_start_3h[b == i].mean()),
              "observed": float(cal.y_start_3h[b == i].mean()), "rows": int((b == i).sum())} for i in range(10) if (b == i).any()]
    L = {"raion": "District", "oblast": "Oblast"}
    head, tg = [], []
    for lv in ("raion", "oblast"):
        for h in (1, 3):
            tab = M[lv][f"start_{h}h"]["table"]
            ch, base = tab["LightGBM (chosen)"], tab["baseline: same hour, last 14 days"]
            head.append({"target": f"New alert within {h}h", "level": L[lv], "model_auc": ch["ROC-AUC"],
                         "baseline_auc": base["ROC-AUC"], "skill": ch["skill vs same-hour"]})
            tg.append({"target": f"New alert within {h}h ({L[lv].lower()})", "without": ch["skill vs same-hour"],
                       "with": tab["LightGBM + @war_monitor"]["skill vs same-hour"],
                       "with_kpszsu": tab["LightGBM + @kpszsu"]["skill vs same-hour"]})
    dn = M["raion"]["start_3h"]["day_night"]
    # 13 Oct update (D58/D59/D55): the validation comparison of the corrected version (validation weeks, not the test)
    upd = json.loads((REP / "local_neighbours_ablation.json").read_text()) if (REP / "local_neighbours_ablation.json").exists() else None
    dump("metrics", {"update_13oct": upd, "test_period": ["2026-09-13", "2026-10-11"], "headline": head, "calibration": calib,
                     "day_night": [{"part": "Day (06-22)", "auc": dn["day (06-22 Kyiv)"]["ROC-AUC"]},
                                   {"part": "Night (22-06)", "auc": dn["night (22-06 Kyiv)"]["ROC-AUC"]}],
                     "telegram": tg, "range_coverage_validation_week": now["range_coverage_validation_week"], "full": M})


if __name__ == "__main__":
    main()

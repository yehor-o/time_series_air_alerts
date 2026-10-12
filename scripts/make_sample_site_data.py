"""SAMPLE data for building the website before the real export exists (task M).

Writes site/data/*.json in exactly the format scripts/export_site.py will write later, filled with
plausible random numbers. Every file carries "sample": true and the site shows a banner for it.

Usage: python scripts/make_sample_site_data.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path("site/data")
RNG = np.random.default_rng(7)


def kyiv_block_starts(t0, n=56):
    """Start times (UTC) of the next n 3-hour Kyiv-clock blocks after t0."""
    local = t0.tz_convert("Europe/Kyiv")
    first = local.floor("h") + pd.Timedelta(hours=(3 - local.hour % 3) % 3 or 3)
    return [(first + pd.Timedelta(hours=3 * i)).tz_convert("UTC") for i in range(n)]


def main():
    shapes = json.loads((OUT / "raions.geojson").read_text())["features"]
    units = [f["properties"] for f in shapes if f["properties"]["status"] == "forecast"]
    oblasts = sorted({u["oblast_id"] for u in units})
    ob_name = {u["oblast_id"]: u["oblast"] for u in units}
    t0 = pd.Timestamp("2026-10-11 09:00", tz="UTC")
    base = {o: RNG.uniform(0.03, 0.6) for o in oblasts}

    def unit_now(b):
        p3 = float(np.clip(b + RNG.normal(0, .08), .01, .97))
        lo = int(RNG.integers(15, 60))
        return {"p1": round(p3 * .45, 3), "p3": round(p3, 3), "red": round(float(RNG.uniform(.05, .8)), 3),
                "dur": [lo, lo + int(RNG.integers(20, 120))], "cnt": [int(b * 4), int(b * 4) + 2],
                "hrs": [round(b * 5, 1), round(b * 5 + 3, 1)],
                "next24": [round(float(np.clip(b + .25 * np.sin(i / 1.3) + RNG.normal(0, .05), .01, .97)), 3) for i in range(8)]}

    now = {"raion": {u["id"]: unit_now(base[u["oblast_id"]]) for u in units},
           "oblast": {o: unit_now(min(base[o] * 1.3, .9)) for o in oblasts}}
    blocks = kyiv_block_starts(t0)
    week = {"block_starts_utc": [b.isoformat() for b in blocks],
            "raion": {u["id"]: [round(float(np.clip(base[u["oblast_id"]] + .2 * np.sin(i / 1.3) + RNG.normal(0, .05), .01, .95)), 3)
                                for i in range(56)] for u in units},
            "oblast": {o: [round(float(np.clip(base[o] * 1.3 + .2 * np.sin(i / 1.3), .01, .95)), 3) for i in range(56)] for o in oblasts}}

    def hist(b):
        alerts, t = [], 0
        while t < 168 * 60:
            t += int(RNG.exponential(600 / (b + .05)))
            d = int(RNG.exponential(50)) + 5
            if t < 168 * 60:
                alerts.append([t, min(t + d, 168 * 60), "red" if RNG.random() < .35 else "yellow"])
            t += d
        pred = [int(np.clip(100 * (b + .2 * np.sin(h / 4) + RNG.normal(0, .05)), 1, 99)) for h in range(168)]
        return {"alerts": alerts, "pred": pred}

    history = {"start_utc": (t0 - pd.Timedelta("168h")).isoformat(), "hours": 168,
               "raion": {u["id"]: hist(base[u["oblast_id"]]) for u in units},
               "oblast": {o: hist(base[o]) for o in oblasts}}
    n = 24 * 28
    start = pd.Timestamp("2026-09-13", tz="UTC")

    def rep(b):
        p = np.clip(b + .2 * np.sin(np.arange(n) / 5) + RNG.normal(0, .08, n), .01, .97)
        return {"p": (p * 100).round().astype(int).tolist(), "y": (RNG.random(n) < p).astype(int).tolist()}

    replay = {"start_utc": start.isoformat(), "hours": n, "horizon_h": 3,
              "raion": {u["id"]: rep(base[u["oblast_id"]]) for u in units}, "oblast": {o: rep(base[o]) for o in oblasts}}
    metrics = {"sample": True, "test_period": ["2026-09-13", "2026-10-11"],
               "headline": [{"target": "New alert within 1h", "level": "District", "model_auc": .84, "baseline_auc": .72, "skill": .18},
                            {"target": "New alert within 3h", "level": "District", "model_auc": .85, "baseline_auc": .73, "skill": .33}],
               "calibration": [{"bin": f"{i * 10}-{i * 10 + 10}%", "predicted": i / 10 + .05, "observed": i / 10 + .05 + RNG.normal(0, .02), "rows": int(5000 / (i + 1))} for i in range(10)],
               "telegram": [{"target": "New alert within 3h (district)", "without": .368, "with": .366}],
               "day_night": [{"part": "Day (06-22)", "auc": .85}, {"part": "Night (22-06)", "auc": .83}]}
    meta = {"sample": True, "title": "Time-Series Air Alert Forecast, Ukraine (demo)",
            "forecast_time_utc": t0.isoformat(), "data_until_utc": "2026-10-11T09:54:00+00:00",
            "units": {"raion": {u["id"]: {"name": u["name"], "oblast": u["oblast"], "oblast_id": u["oblast_id"]} for u in units},
                      "oblast": {o: {"name": ob_name[o]} for o in oblasts}}}
    for name, obj in (("meta", meta), ("now", now), ("week", week), ("history", history), ("replay", replay), ("metrics", metrics)):
        obj["sample"] = True
        (OUT / f"{name}.json").write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")))
        print(name, f"{(OUT / f'{name}.json').stat().st_size / 1e3:.0f} kB")


if __name__ == "__main__":
    main()

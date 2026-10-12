"""Map shapes for the website (task H): match raions to boundaries, simplify, export.

Source: data/raw/vadimkin/ukr_admin2.geojson (OCHA admin-2 boundaries, valid from 2025-09-01, 26 MB).
Output: site/data/raions.geojson (< 1 MB) and reports/map_preview.png.

Every one of our 119 forecast units must match a shape (the script fails otherwise). Shapes we don't
forecast are kept for context: Crimea, Sevastopol and Luhansk (permanent alerts), the Chornobyl zone.

Simplification is a plain Douglas-Peucker on each ring (drops points that move the outline by less than
TOL degrees, about 1 km), then coordinates are rounded to 3 decimals (about 100 m).

Usage: PYTHONPATH=. python scripts/build_map.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.alerts.sources import name_key

SRC = Path("data/raw/vadimkin/ukr_admin2.geojson")
OUT = Path("site/data/raions.geojson")
TOL = 0.008
# boundaries use the 2024 names, our data the older official ones (decisions.md D27)
RENAMED = {"Володимирський": "Володимир-Волинський район", "Шептицький": "Червоноградський район",
           "Берестинський": "Красноградський район"}
PERMANENT = {"Автономна Республіка Крим", "Севастополь", "Луганська"}


def dp(points, tol):
    """Douglas-Peucker simplification of a polyline (n x 2 array)."""
    if len(points) < 3:
        return points
    keep = np.zeros(len(points), bool)
    keep[[0, -1]] = True
    stack = [(0, len(points) - 1)]
    while stack:
        a, b = stack.pop()
        if b <= a + 1:
            continue
        seg = points[b] - points[a]
        rel = points[a + 1:b] - points[a]
        norm = np.hypot(*seg)
        d = np.abs(seg[0] * rel[:, 1] - seg[1] * rel[:, 0]) / norm if norm else np.hypot(rel[:, 0], rel[:, 1])
        i = int(np.argmax(d))
        if d[i] > tol:
            m = a + 1 + i
            keep[m] = True
            stack += [(a, m), (m, b)]
    return points[keep]


def simplify_polygon(rings):
    out = []
    for k, ring in enumerate(rings):
        r = dp(np.asarray(ring, float), TOL)
        if len(r) < 4:  # a ring that collapsed: keep the outer one minimal, drop holes/islets
            if k > 0:
                continue
            r = np.asarray(ring, float)[:: max(len(ring) // 4, 1)]
            r = np.vstack([r, r[:1]])
        out.append(np.round(r, 3).tolist())
    return out


def main():
    g = json.loads(SRC.read_text())
    units = pd.read_csv("data/processed/raions.csv")
    by_key = {(o, name_key(r.replace("район", ""))): (o, r) for o, r in zip(units.oblast, units.raion)}
    feats, matched = [], set()
    for f in g["features"]:
        p = f["properties"]
        ob_uk = "м. Київ" if p["adm1_name1"] == "Київ" else f"{p['adm1_name1']} область"
        rn = RENAMED.get(p["adm2_name1"], p["adm2_name1"])
        unit = by_key.get((ob_uk, name_key(rn.replace("район", "")))) if ob_uk != "м. Київ" else ("м. Київ", "м. Київ")
        status = "forecast" if unit else ("permanent" if p["adm1_name1"] in PERMANENT else "nodata")
        if unit:
            matched.add(unit)
        geom = f["geometry"]
        polys = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
        polys = [simplify_polygon(pl) for pl in polys]
        polys = [pl for pl in polys if pl and len(pl[0]) >= 4]
        row = units[(units.oblast == unit[0]) & (units.raion == unit[1])].iloc[0] if unit else None
        feats.append({"type": "Feature",
                      "properties": {"id": f"{unit[0]}|{unit[1]}" if unit else None, "status": status,
                                     "name": "Kyiv City" if ob_uk == "м. Київ" else f"{p['adm2_name']} district",
                                     "oblast": row.oblast_en if row is not None else p["adm1_name"],
                                     "oblast_id": unit[0] if unit else None,
                                     "name_uk": p["adm2_name1"]},
                      "geometry": {"type": "MultiPolygon", "coordinates": polys}})
    missing = set(zip(units.oblast, units.raion)) - matched
    if missing:
        raise SystemExit(f"unmatched forecast units: {missing}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False, separators=(",", ":")))
    print(f"{len(feats)} shapes ({sum(f['properties']['status'] == 'forecast' for f in feats)} forecast units) "
          f"-> {OUT} ({OUT.stat().st_size / 1e6:.2f} MB)")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(12, 8), facecolor="#0b1424")
    colors = {"forecast": "#2f4b6e", "permanent": "#5a2a33", "nodata": "#3a3f47"}
    for f in feats:
        for pl in f["geometry"]["coordinates"]:
            x, y = np.array(pl[0]).T
            ax.fill(x, y, color=colors[f["properties"]["status"]], ec="#8aa0bf", lw=0.3)
    ax.set_aspect(1 / np.cos(np.radians(48.5)))
    ax.axis("off")
    fig.savefig("reports/map_preview.png", dpi=110, bbox_inches="tight", facecolor=fig.get_facecolor())
    print("preview -> reports/map_preview.png")


if __name__ == "__main__":
    main()

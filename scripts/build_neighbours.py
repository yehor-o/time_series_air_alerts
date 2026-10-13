"""Which districts share a border (D55): data/neighbours.json, used for the "next door" model inputs.

Source: data/raw/vadimkin/ukr_admin2.geojson (full-detail OCHA admin-2 boundaries; the website file is simplified to
~1 km and could miss short borders). Two districts are neighbours when at least MIN_SHARED boundary points of one lie
within TOL degrees (~200 m) of the other's boundary; a single touching corner does not count. Oblasts are neighbours
when any of their districts are. Districts we do not forecast (Luhansk, Crimea, Chornobyl zone) are left out.
SciPy (already installed with scikit-learn) does the nearest-point search.

Usage: PYTHONPATH=. python scripts/build_neighbours.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from build_map import RENAMED, SRC
from src.alerts.sources import name_key

OUT = Path("data/neighbours.json")
TOL = 0.002
MIN_SHARED = 3


def unit_points():
    g = json.loads(SRC.read_text())
    units = pd.read_csv("data/processed/raions.csv")
    by_key = {(o, name_key(r.replace("район", ""))): f"{o}|{r}" for o, r in zip(units.oblast, units.raion)}
    pts = {}
    for f in g["features"]:
        p = f["properties"]
        ob = "м. Київ" if p["adm1_name1"] == "Київ" else f"{p['adm1_name1']} область"
        rn = RENAMED.get(p["adm2_name1"], p["adm2_name1"])
        unit = "м. Київ|м. Київ" if ob == "м. Київ" else by_key.get((ob, name_key(rn.replace("район", ""))))
        if unit is None:
            continue
        geom = f["geometry"]
        polys = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
        xy = np.concatenate([np.asarray(ring)[:, :2] for poly in polys for ring in poly])
        pts[unit] = np.concatenate([pts[unit], xy]) if unit in pts else xy
    missing = set(by_key.values()) | {"м. Київ|м. Київ"}
    missing -= set(pts)
    if missing:
        raise SystemExit(f"units without a shape: {missing}")
    return pts


def main():
    pts = unit_points()
    names = sorted(pts)
    trees = {u: cKDTree(pts[u]) for u in names}
    lo = {u: pts[u].min(0) for u in names}
    hi = {u: pts[u].max(0) for u in names}
    nb = {u: [] for u in names}
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if (lo[a] > hi[b] + TOL).any() or (lo[b] > hi[a] + TOL).any():
                continue  # bounding boxes apart
            d, _ = trees[b].query(pts[a], distance_upper_bound=TOL)
            if np.isfinite(d).sum() >= MIN_SHARED:
                nb[a].append(b)
                nb[b].append(a)
    ob = {}
    for a, lst in nb.items():
        oa = a.split("|")[0]
        ob.setdefault(oa, set()).update(b.split("|")[0] for b in lst if b.split("|")[0] != oa)
    out = {"raion": {u: sorted(v) for u, v in nb.items()}, "oblast": {o: sorted(v) for o, v in sorted(ob.items())}}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    n = np.array([len(v) for v in nb.values()])
    print(f"{len(names)} districts, neighbours per district: min {n.min()}, median {np.median(n):.0f}, max {n.max()}; "
          f"{sum(len(v) for v in ob.values()) // 2} oblast pairs -> {OUT}")
    lonely = [u for u, v in nb.items() if not v]
    if lonely:
        raise SystemExit(f"districts without neighbours: {lonely}")


if __name__ == "__main__":
    main()

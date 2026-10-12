"""@war_monitor features per issue hour (leakage-safe: only posts published before t).

Nationwide (same for every unit):
  wm_posts_{w}h, wm_missile_{w}h, wm_drone_{w}h, wm_kab_{w}h   number of posts of each kind in [t-w, t)
  wm_drones_counted_{w}h   sum of drone counts written in posts ("13х БпЛА") in [t-w, t)
  wm_strat_aviation        1 if the latest daily situation post before t says strategic aviation is active
  wm_silent_6h             1 if the channel posted nothing in [t-6h, t) (feed gap, not "calm")
Per oblast (raion rows use their oblast):
  wm_reg_posts_{w}h, wm_reg_missile_{w}h, wm_reg_drone_{w}h  posts naming the oblast in [t-w, t)
"""
import re

import numpy as np
import pandas as pd

from .war_monitor import tag_posts

COUNT = re.compile(r"(\d{1,3})\s*[хx]\s*(?:бпла|шахед|ударн|реактив|дрон)", re.I)
WINDOWS = (3, 6, 24)


def _past(x, w):
    c = np.concatenate([[0], np.cumsum(x)])
    k = np.arange(len(x))
    return c[k] - c[np.maximum(k - w, 0)]


def war_monitor_features(posts, grid, oblasts):
    """posts: raw @war_monitor posts (id, published, text). grid: tz-aware hourly DatetimeIndex.
    Returns (national DataFrame indexed by time, regional DataFrame indexed by (oblast, time))."""
    p = tag_posts(posts)
    p = p[p.published < grid[-1] + pd.Timedelta("1h")]
    g = pd.DatetimeIndex(grid).tz_convert(None)
    edges = np.append(g.values, g.values[-1] + np.timedelta64(1, "h")).astype("datetime64[ns]").view("int64")
    pub = p.published.dt.tz_convert(None).values.astype("datetime64[ns]").view("int64")

    def hist(mask, weights=None):
        return np.histogram(pub[mask], bins=edges, weights=None if weights is None else weights[mask])[0]

    ones = np.ones(len(p), bool)
    counts = p.text.fillna("").map(lambda s: sum(int(n) for n in COUNT.findall(s))).values.astype(float)
    nat = {}
    for name, m in {"posts": ones, "missile": p.missile.values, "drone": p.drone.values, "kab": p.kab.values}.items():
        h = hist(m)
        for w in WINDOWS:
            nat[f"wm_{name}_{w}h"] = _past(h, w)
    hc = hist(ones, counts)
    for w in WINDOWS:
        nat[f"wm_drones_counted_{w}h"] = _past(hc, w)
    nat["wm_silent_6h"] = (nat["wm_posts_6h"] == 0).astype(float)
    # strategic aviation status from the latest situation summary published before t
    summ = p[p.text.str.contains("Стратегічна авіація", case=False, na=False)]
    active = ~summ.text.str.contains(r"Стратегічна авіація:\s*\n?\s*Не активна", case=False, regex=True)
    sp = summ.published.dt.tz_convert(None).values.astype("datetime64[ns]")
    idx = np.searchsorted(sp, g.values.astype("datetime64[ns]"), side="left") - 1  # strictly before t
    nat["wm_strat_aviation"] = np.where(idx >= 0, active.values[np.maximum(idx, 0)].astype(float), np.nan)
    national = pd.DataFrame(nat, index=pd.DatetimeIndex(grid, name="time"))

    regs = []
    for ob in oblasts:
        named = p.oblasts.map(lambda l: ob in l).values
        r = {}
        for name, m in {"posts": named, "missile": named & p.missile.values, "drone": named & p.drone.values}.items():
            h = hist(m)
            for w in WINDOWS:
                r[f"wm_reg_{name}_{w}h"] = _past(h, w)
        regs.append(pd.DataFrame(r, index=pd.DatetimeIndex(grid, name="time")).assign(oblast=ob))
    regional = pd.concat(regs).reset_index().set_index(["oblast", "time"])
    return national, regional


def add_war_monitor(panel, national, regional):
    out = panel.join(national, on="time")
    return out.join(regional, on=["oblast", "time"])

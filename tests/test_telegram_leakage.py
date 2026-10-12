"""Telegram features at hour t must not change if all posts published at or after t are deleted."""
import numpy as np
import pandas as pd

from src.alerts.telegram_features import war_monitor_features


def synthetic_posts(n=600, seed=0):
    rng = np.random.default_rng(seed)
    t0 = pd.Timestamp("2026-01-01", tz="UTC")
    pub = t0 + pd.to_timedelta(np.sort(rng.uniform(0, 10 * 24 * 3600, n)), unit="s")
    texts = rng.choice(["БпЛА повз Харків", "Ракети на Київщину", "13х БпЛА Одеса", "КАБ на Запоріжжя", "Відбій"], n)
    return pd.DataFrame({"id": np.arange(n), "published": pub, "text": texts})


def test_features_ignore_posts_from_t_on():
    posts = synthetic_posts()
    grid = pd.date_range("2026-01-03", "2026-01-10", freq="h", tz="UTC")
    obl = ["Харківська область", "Одеська область"]
    nat, reg = war_monitor_features(posts, grid, obl)
    for k in (30, 77, 140):
        t = grid[k]
        known = posts[posts.published < t]
        n2, r2 = war_monitor_features(known, grid[: k + 1], obl)
        pd.testing.assert_series_equal(nat.loc[t].drop("wm_strat_aviation"), n2.loc[t].drop("wm_strat_aviation"),
                                       check_names=False, check_exact=False)
        pd.testing.assert_series_equal(reg.xs(t, level="time").loc["Харківська область"],
                                       r2.xs(t, level="time").loc["Харківська область"], check_names=False)

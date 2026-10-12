"""@war_monitor posts: threat type and region mentions.

Role (user, 2026-10-12): alerts themselves come from the official data / alerts.in.ua; @war_monitor
is used to tell WHAT kind of threat is going on (drones vs missiles), not WHETHER there is an alert.
"""
import re

import pandas as pd

MISSILE = re.compile(r"\bкр\b|крилат|ракет|балістик|циркон|кинджал|іскандер|калібр|х-\d|🟣|міг-31|ту-95|ту-22|ту-160"
                     r"|стратегічна авіація: актив|пуск", re.I)
KAB = re.compile(r"\bкаб|авіабомб", re.I)
DRONE = re.compile(r"бпла|шахед|реактив|мопед|дрон|герань|гербер", re.I)
ALL_CLEAR = re.compile(r"відбій|чисто", re.I)

# Stems of oblast names, regional forms ("-щина") and main cities, as written in @war_monitor posts.
OBLAST_STEMS = {
    "Вінницька область": r"вінниц|вінничин|гайсин|тульчин|жмерин",
    "Волинська область": r"волин|луцьк|ковел",
    "Дніпропетровська область": r"дніпропетров|дніпр[оау]\b|дніпрі|кривий ріг|кривого рогу|криворіж|нікопол|павлоград|кам.янськ|марганц",
    "Донецька область": r"донеч|краматор|слов.янськ|покровськ|дружків|костянтинів",
    "Житомирська область": r"житомир|коростен|бердичів|звягел",
    "Закарпатська область": r"закарпат|ужгород|мукачев",
    "Запорізька область": r"запоріж",
    "Івано-Франківська область": r"франків|прикарпат|калуш",
    "Київська область": r"київщин|біла церква|білої церкви|бровар|бориспіл|обухів|фастів|вишгород|бучанськ|ірпін",
    "м. Київ": r"київ(?!щин)|києв|столиц",
    "Кіровоградська область": r"кіровоград|кропивниц|олександрі[яї]|світловодськ",
    "Львівська область": r"львів",
    "Миколаївська область": r"миколаїв|вознесенськ|первомайськ",
    "Одеська область": r"одес|ізмаїл|південне|чорноморськ|затоку|затока",
    "Полтавська область": r"полтав|кременчук|миргород|лубн",
    "Рівненська область": r"рівне|рівного|рівненщ|дубн",
    "Сумська область": r"сумщин|\bсуми\b|\bсум\b|сумськ|шостк|конотоп|охтирк|ромн|ромен",
    "Тернопільська область": r"тернопіл",
    "Харківська область": r"харків|чугуїв|ізюм|куп.янськ|лозов|богодухів",
    "Херсонська область": r"херсон",
    "Хмельницька область": r"хмельниц|старокостянтин|шепетівк|кам.янець",
    "Черкаська область": r"черкас|умань|умані|золотонош|сміл",
    "Чернівецька область": r"чернівц|буковин",
    "Чернігівська область": r"черніг|ніжин|прилук|новгород-сівер|корюків",
}
OBLAST_RE = {k: re.compile(v, re.I) for k, v in OBLAST_STEMS.items()}


def tag_posts(posts):
    """Add threat flags and the list of mentioned oblasts to every post."""
    p = posts.copy()
    t = p.text.fillna("")
    p["missile"] = t.str.contains(MISSILE)
    p["kab"] = t.str.contains(KAB)
    p["drone"] = t.str.contains(DRONE)
    p["all_clear"] = t.str.contains(ALL_CLEAR) & ~p.missile & ~p.drone
    p["oblasts"] = t.map(lambda s: [k for k, r in OBLAST_RE.items() if r.search(s)])
    return p


def window_counts(posts, times, oblasts, before, after):
    """For each (time, oblast): number of missile / drone posts nationwide and mentioning the oblast,
    published in [time - before, time + after)."""
    p = posts.sort_values("published").reset_index(drop=True)
    pub = p.published.values
    out = []
    for t, ob in zip(times, oblasts):
        lo, hi = pub.searchsorted((t - before).to_datetime64()), pub.searchsorted((t + after).to_datetime64())
        w = p.iloc[lo:hi]
        reg = w.oblasts.map(lambda l: ob in l)
        out.append({"nat_missile": int(w.missile.sum()), "nat_drone": int(w.drone.sum()), "nat_kab": int(w.kab.sum()),
                    "reg_missile": int((w.missile & reg).sum()), "reg_drone": int((w.drone & reg).sum()),
                    "reg_posts": int(reg.sum())})
    return pd.DataFrame(out)

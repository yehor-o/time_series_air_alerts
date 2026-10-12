"""Loading the raw alert sources into one common shape.

Common columns: oblast, raion, hromada (Ukrainian official names), loc_level (oblast|raion|hromada),
start, end (UTC), plus source-specific columns. Raion names are normalised to the official
(Vadimkin) spelling; see RAION_RENAMES / CITY_TO_RAION.
"""
import re

import pandas as pd

# The official feed (@air_alert_ua) is complete until it stopped; the alerts.in.ua archive is
# complete from ARCHIVE_COMPLETE_FROM (decisions.md D19).
OFFICIAL_LAST = pd.Timestamp("2026-09-07 06:10", tz="UTC")
ARCHIVE_COMPLETE_FROM = pd.Timestamp("2026-09-06 12:00", tz="UTC")
EXCLUDED_OBLASTS = {"Луганська область", "Автономна Республіка Крим"}  # permanent sirens
KYIV_CITY = "м. Київ"

# alerts.in.ua uses the 2024 renamed raions; the official dataset kept the old names.
RAION_RENAMES = {
    "Володимирський район": "Володимир-Волинський район",
    "Шептицький район": "Червоноградський район",
    "Берестинський район": "Красноградський район",
}
# alerts.in.ua "city" records have no raion; the city lies in this raion.
CITY_TO_RAION = {
    "м. Харків": "Харківський район",
    "м. Дніпро": "Дніпровський район",
    "м. Запоріжжя": "Запорізький район",
    "м. Нікополь": "Нікопольський район",
    "м. Марганець": "Нікопольський район",
    "м. Кривий Ріг": "Криворізький район",
    "м. Світловодськ": "Олександрійський район",
}


def norm(s):
    """Unify apostrophes and spaces (sources mix ’, ʼ and ')."""
    return s.str.replace("’", "'", regex=False).str.replace("ʼ", "'", regex=False).str.strip()


def name_key(s):
    """Letters only, lower case: matches '#Камянський_район' with 'Кам’янський район'."""
    return re.sub(r"[^a-zа-яіїєґ]", "", str(s).lower())


def load_official(path_uk, path_en=None):
    o = pd.read_csv(path_uk, parse_dates=["started_at", "finished_at"])
    o = o.rename(columns={"started_at": "start", "finished_at": "end", "level": "loc_level"})
    for c in ("oblast", "raion", "hromada"):
        o[c] = norm(o[c].astype("string"))
    if path_en:
        e = pd.read_csv(path_en, usecols=["oblast", "raion"])
        o["oblast_en"], o["raion_en"] = e.oblast.values, e.raion.values
    o["row_id"] = range(len(o))
    return o


def load_archive(path):
    a = pd.read_csv(path, parse_dates=["started_at", "finished_at"])
    a = a.rename(columns={"started_at": "start", "finished_at": "end"})
    a["oblast"] = norm(a.location_oblast.astype("string"))
    title = norm(a.location_title.astype("string"))
    raion = norm(a.location_raion.astype("string"))
    a["raion"] = pd.Series(pd.NA, index=a.index, dtype="string")
    a["hromada"] = pd.Series(pd.NA, index=a.index, dtype="string")
    a.loc[a.location_type == "raion", "raion"] = title
    a.loc[a.location_type == "hromada", "raion"] = raion
    a.loc[a.location_type == "hromada", "hromada"] = title
    is_city = a.location_type == "city"
    a.loc[is_city, "raion"] = title[is_city].map(CITY_TO_RAION)
    a.loc[is_city, "hromada"] = title[is_city]
    a["raion"] = a.raion.replace(RAION_RENAMES)
    kyiv = a.location_title == KYIV_CITY
    a.loc[kyiv, "oblast"] = KYIV_CITY
    a["loc_level"] = a.location_type.replace({"city": "hromada"})
    a.loc[kyiv, "loc_level"] = "oblast"
    a["red"] = a.alert_level.eq("red")
    return a


def load_volunteer(path_uk):
    v = pd.read_csv(path_uk, parse_dates=["started_at", "finished_at"])
    v = v.rename(columns={"started_at": "start", "finished_at": "end", "region": "oblast"})
    v["oblast"] = norm(v.oblast.astype("string")).replace({"Київ": KYIV_CITY})
    return v


def raion_universe(official, since="2025-06-01"):
    """Raions per oblast (official spelling) + Kyiv City as a single unit. Excludes permanent-siren regions."""
    r = official[(official.loc_level == "raion") & (official.start >= pd.Timestamp(since, tz="UTC"))]
    u = r[["oblast", "raion", "oblast_en", "raion_en"]].drop_duplicates(["oblast", "raion"])
    kyiv = official[official.oblast == KYIV_CITY][["oblast", "oblast_en"]].head(1).assign(raion=KYIV_CITY, raion_en="Kyiv City")
    u = pd.concat([u, kyiv], ignore_index=True)
    return u[~u.oblast.isin(EXCLUDED_OBLASTS)].sort_values(["oblast", "raion"]).reset_index(drop=True)

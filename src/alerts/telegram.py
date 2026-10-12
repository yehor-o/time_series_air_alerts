"""Telegram messages: loading scraped channels and labelling official alerts by message type.

The Vadimkin parser turned every @air_alert_ua message whose first line has 🔴 into an "alert",
so artillery threats, drone threats and urban-fight warnings ended up in the official dataset
(decisions.md D20). Its `started_at` is exactly the message time, and the message's last line holds
the location hashtags, so each official row can be traced back to the message that created it.
"""
import glob
import json

import pandas as pd

from .sources import name_key

KINDS = ["air_raid", "artillery", "drone_threat", "missile_threat", "ballistic_threat", "kab_threat",
         "radiation", "urban_fights", "other"]


def load_channel(pattern):
    """All scraped posts matching a glob pattern (several part files allowed), de-duplicated by id."""
    rows = [json.loads(line) for f in sorted(glob.glob(pattern)) for line in open(f, encoding="utf-8")]
    m = pd.DataFrame(rows).drop_duplicates("id").sort_values("id").reset_index(drop=True)
    m["published"] = pd.to_datetime(m.published, utc=True)
    return m


def classify(text):
    """Message type of an @air_alert_ua post (start and all-clear posts get the same type)."""
    t = text.lower()
    if "вуличних боїв" in t:
        return "urban_fights"
    if "артобстріл" in t:
        return "artillery"
    if "бпла" in t or "дронів" in t:
        return "drone_threat"
    if "балістик" in t:
        return "ballistic_threat"
    if "ракетна загроза" in t or "ракетної загрози" in t:
        return "missile_threat"
    if "авіабомб" in t:
        return "kab_threat"
    if "радіаційн" in t:
        return "radiation"
    if "повітряна тривога" in t or "відбій тривоги" in t:
        return "air_raid"
    return "other"


def parse_air_alert_ua(messages):
    """Add kind, is_start (what the Vadimkin parser counted as an alert start) and location keys."""
    m = messages.copy()
    first = m.text.str.split("\n").str[0]
    m["kind"] = m.text.map(classify)
    m["is_start"] = first.str.contains("🔴") | first.str.contains("Повітряна", regex=False)
    m["is_start"] &= ~first.str.contains("Відбій", regex=False)
    last = m.text.str.split("\n").str[-1].str.lower().replace({"#херсон": "#м_херсон_та_херсонська_територіальна_громада"})
    m["loc_keys"] = last.map(lambda s: [name_key(x) for x in s.split() if x.startswith("#")])
    return m


def label_official(official, messages):
    """Add `kind` (message type) and `label_how` to every official row.

    Match 1: same timestamp and the row's location is among the message hashtags.
    Match 2: same timestamp only, if every start message in that second has the same kind.
    Rows outside the scraped period or without a matching message get kind 'unknown'.
    """
    m = parse_air_alert_ua(messages)
    starts = m[m.is_start]
    o = official.copy()
    loc = o.hromada.where(o.loc_level == "hromada", o.raion.where(o.loc_level == "raion", o.oblast))
    o["loc_key"] = loc.map(name_key)
    ex = starts[["published", "kind", "loc_keys"]].explode("loc_keys").rename(columns={"loc_keys": "loc_key"})
    ex = ex.drop_duplicates(["published", "loc_key"])
    o = o.merge(ex, left_on=["start", "loc_key"], right_on=["published", "loc_key"], how="left").drop(columns="published")
    o["label_how"] = o.kind.notna().map({True: "time+location", False: None})
    same_kind = starts.groupby("published").kind.agg(lambda k: k.iloc[0] if k.nunique() == 1 else None).dropna()
    fallback = o.kind.isna() & o.start.isin(same_kind.index)
    o.loc[fallback, "kind"] = o.loc[fallback, "start"].map(same_kind)
    o.loc[fallback, "label_how"] = "time only"
    covered = o.start.between(m.published.min(), m.published.max())
    o["kind"] = o.kind.fillna("unknown")
    o.loc[~covered & (o.kind == "unknown"), "label_how"] = "outside scraped period"
    o.loc[covered & (o.kind == "unknown"), "label_how"] = "no message found"
    return o.drop(columns="loc_key")

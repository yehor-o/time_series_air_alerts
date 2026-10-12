"""Fetch the latest alerts from the alerts.in.ua API into the archive file (live forecasts, D52).

The JustJimer archive (data/raw/justjimer/alerts_in_ua.csv) is a daily copy of this same API, stored as the API's own
fields, one row per alert id. This script reads the last month for every region we forecast and upserts the rows by id,
so the archive becomes up to date to the minute; build_alert_table.py then reads it as usual. Re-reading a whole month
each time makes it self-repairing: a failed run loses nothing, and alerts that were running get their end time later.

API limits: the history endpoint allows 2 requests per minute, so 25 regions take about 13 minutes.
The token is read from the environment variable ALERTS_IN_UA_TOKEN (a GitHub Actions secret); it is never printed.

Usage: ALERTS_IN_UA_TOKEN=... python scripts/fetch_live.py [--archive data/raw/justjimer/alerts_in_ua.csv]
"""
import argparse
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://api.alerts.in.ua/v1"
# Region ids from the API documentation; Luhansk (16), Crimea (29) and Sevastopol (30) are permanent alerts we do not forecast.
REGIONS = {3: "Хмельницька", 4: "Вінницька", 5: "Рівненська", 8: "Волинська", 9: "Дніпропетровська", 10: "Житомирська",
           11: "Закарпатська", 12: "Запорізька", 13: "Івано-Франківська", 14: "Київська", 15: "Кіровоградська",
           17: "Миколаївська", 18: "Одеська", 19: "Полтавська", 20: "Сумська", 21: "Тернопільська", 22: "Харківська",
           23: "Херсонська", 24: "Черкаська", 25: "Чернігівська", 26: "Чернівецька", 27: "Львівська", 28: "Донецька",
           31: "м. Київ"}
COLUMNS = ["id", "location_uid", "location_type", "location_title", "location_oblast", "location_raion",
           "started_at", "finished_at", "alert_type", "alert_level", "threats"]
PAUSE = 31  # seconds between history requests (limit: 2 per minute)


def get(path, token, tries=3):
    req = urllib.request.Request(f"{BASE}/{path}", headers={"Authorization": f"Bearer {token}", "Accept": "application/json",
                                                           "User-Agent": "time_series_air_alerts (github.com/yehor-o)"})
    for k in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (401, 403) or k == tries - 1:
                raise SystemExit(f"{path}: HTTP {e.code} ({ {401: 'bad or missing token', 403: 'blocked', 429: 'rate limit'}.get(e.code, e.reason)})")
            time.sleep(PAUSE * (k + 1))
        except urllib.error.URLError as e:
            if k == tries - 1:
                raise SystemExit(f"{path}: {e.reason}")
            time.sleep(10)


def row(a):
    return {"id": str(a.get("id", "")), "location_uid": a.get("location_uid") or "", "location_type": a.get("location_type") or "",
            "location_title": a.get("location_title") or "", "location_oblast": a.get("location_oblast") or "",
            "location_raion": a.get("location_raion") or "", "started_at": a.get("started_at") or "",
            "finished_at": a.get("finished_at") or "", "alert_type": a.get("alert_type") or "",
            "alert_level": a.get("alert_level") or "",
            "threats": ";".join(f"{t.get('threat_type', '?')}:{t.get('level', '?')}" for t in (a.get("threats") or []))}


def main(archive):
    token = os.environ.get("ALERTS_IN_UA_TOKEN", "")
    if not token:
        sys.exit("ALERTS_IN_UA_TOKEN is not set")
    path = Path(archive)
    with path.open(encoding="utf-8", newline="") as f:
        rows = {r["id"]: r for r in csv.DictReader(f)}
    before, new, changed = len(rows), 0, 0
    for k, (uid, name) in enumerate(REGIONS.items()):
        if k:
            time.sleep(PAUSE)
        alerts = get(f"regions/{uid}/alerts/month_ago.json", token).get("alerts", [])
        n0, c0 = new, changed
        for a in alerts:
            r = row(a)
            if not r["id"]:
                continue
            old = rows.get(r["id"])
            new += old is None
            changed += old is not None and old != r
            rows[r["id"]] = r
        print(f"[{k + 1:>2}/{len(REGIONS)}] {name:<18} {len(alerts):>4} alerts  +{new - n0} new  ~{changed - c0} updated", flush=True)
    ordered = sorted(rows.values(), key=lambda r: (r["started_at"], r["id"]))
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(ordered)
    latest = max(r["started_at"] for r in ordered)
    print(f"archive: {before:,} -> {len(rows):,} records ({new} new, {changed} updated); latest start {latest}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive", default="data/raw/justjimer/alerts_in_ua.csv")
    main(ap.parse_args().archive)

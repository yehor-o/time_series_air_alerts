"""Download the alert datasets at pinned commits into data/raw/.

Sources (see decisions.md D1, D19):
  vadimkin   https://github.com/Vadimkin/ukrainian-air-raid-sirens-dataset   (official + volunteer CSVs, raion geojson)
  justjimer  https://github.com/JustJimer/ukraine-air-alert-stats            (alerts.in.ua archive since 2026-09-06)

Without arguments the current HEAD of each repo is resolved and written to data/versions.json,
so every later step can say exactly which data it used. Pass --pin to reuse the commits in versions.json.

Usage:
    python scripts/download_data.py          # latest commits
    python scripts/download_data.py --pin    # re-download the commits recorded in data/versions.json
"""
import argparse
import json
import subprocess
from pathlib import Path

import requests

RAW = Path("data/raw")
SOURCES = {
    "vadimkin": {
        "repo": "Vadimkin/ukrainian-air-raid-sirens-dataset",
        "files": ["datasets/official_data_uk.csv", "datasets/official_data_en.csv",
                  "datasets/volunteer_data_uk.csv", "datasets/volunteer_data_en.csv",
                  "example/ukr_admin2.geojson"],
    },
    "justjimer": {
        "repo": "JustJimer/ukraine-air-alert-stats",
        "files": ["archive/alerts_in_ua.csv"],
    },
}


def head_commit(repo):
    out = subprocess.run(["git", "ls-remote", f"https://github.com/{repo}.git", "HEAD"],
                         capture_output=True, text=True, check=True).stdout
    return out.split()[0]


def main(pin):
    versions_path = Path("data/versions.json")
    versions = json.loads(versions_path.read_text()) if pin else {}
    for name, src in SOURCES.items():
        sha = versions[name]["commit"] if pin else head_commit(src["repo"])
        versions[name] = {"repo": src["repo"], "commit": sha}
        for f in src["files"]:
            dest = RAW / name / Path(f).name
            dest.parent.mkdir(parents=True, exist_ok=True)
            url = f"https://raw.githubusercontent.com/{src['repo']}/{sha}/{f}"
            r = requests.get(url, timeout=120)
            r.raise_for_status()
            dest.write_bytes(r.content)
            print(f"{name}@{sha[:8]}  {f}  ->  {dest}  ({len(r.content) / 1e6:.1f} MB)")
    versions_path.write_text(json.dumps(versions, indent=2) + "\n")
    print("versions written to", versions_path)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pin", action="store_true", help="use the commits stored in data/versions.json")
    main(ap.parse_args().pin)

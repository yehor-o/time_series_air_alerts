"""Scrape a public Telegram channel through its web preview (https://t.me/s/<channel>).

No account or API key is needed. The preview shows ~20 posts per page; we walk
backwards in time with the `?before=<post_id>` parameter.

Output: one JSON object per line (JSONL) with
    id         post number inside the channel
    published  publication time, UTC, ISO 8601 (this is what we use for "known before t")
    edited     True if Telegram marks the post as edited (text may differ from the original!)
    text       message text (plain, line breaks kept)

Usage:
    python scripts/scrape_telegram.py war_monitor --out data/raw/telegram/war_monitor.jsonl \
        --until 2026-01-01 --delay 1.0
"""
import argparse
import json
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

URL = "https://t.me/s/{channel}"
HEADERS = {"User-Agent": "Mozilla/5.0 (research project: air-alert forecasting)"}


def fetch_page(channel, before=None, session=None):
    """Return the posts on one preview page, oldest first."""
    params = {"before": before} if before else None
    for attempt in range(5):  # the connection drops now and then: retry with backoff
        try:
            resp = (session or requests).get(URL.format(channel=channel), params=params, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            break
        except requests.RequestException:
            if attempt == 4:
                raise
            time.sleep(2 ** (attempt + 1))
    soup = BeautifulSoup(resp.text, "lxml")
    posts = []
    for msg in soup.select("div.tgme_widget_message[data-post]"):
        post_id = int(msg["data-post"].split("/")[-1])
        time_tag = msg.select_one("a.tgme_widget_message_date time[datetime]")
        text_tag = msg.select_one("div.tgme_widget_message_text")
        meta = msg.select_one("span.tgme_widget_message_meta")
        posts.append({
            "id": post_id,
            "published": time_tag["datetime"] if time_tag else None,
            "edited": bool(meta and "edited" in meta.get_text()),
            "text": text_tag.get_text("\n", strip=True) if text_tag else "",
        })
    return sorted(posts, key=lambda p: p["id"])


def scrape(channel, out, until=None, delay=1.0, max_pages=None, start_before=None, stop_id=None):
    """Walk backwards from the newest post (or from `start_before`) until `until` (ISO date, UTC),
    `stop_id`, or the channel start. Several runs with disjoint id ranges can run in parallel."""
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    seen = set()
    if out.exists():
        seen = {json.loads(line)["id"] for line in out.open(encoding="utf-8")}
    before, pages = (min(seen) if seen else start_before), 0
    with requests.Session() as session, out.open("a", encoding="utf-8") as f:
        while True:
            posts = fetch_page(channel, before, session)
            new = [p for p in posts if p["id"] not in seen]
            if not posts or not new:
                break
            for p in new:
                f.write(json.dumps(p, ensure_ascii=False) + "\n")
                seen.add(p["id"])
            before, pages = posts[0]["id"], pages + 1
            oldest = posts[0]["published"]
            print(f"page {pages}: posts {posts[0]['id']}-{posts[-1]['id']}, oldest {oldest}", flush=True)
            if (until and oldest and oldest < until) or (max_pages and pages >= max_pages) \
                    or (stop_id and posts[0]["id"] <= stop_id):
                break
            time.sleep(delay)
    return len(seen)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("channel")
    ap.add_argument("--out", required=True)
    ap.add_argument("--until", help="stop once posts are older than this UTC date, e.g. 2026-01-01")
    ap.add_argument("--delay", type=float, default=1.0, help="seconds between requests (be polite)")
    ap.add_argument("--max-pages", type=int)
    ap.add_argument("--start-before", type=int, help="start below this post id instead of the newest post")
    ap.add_argument("--stop-id", type=int, help="stop once posts at or below this id are reached")
    a = ap.parse_args()
    print("total posts saved:", scrape(a.channel, a.out, a.until, a.delay, a.max_pages, a.start_before, a.stop_id))

# Project State

_Last updated: 2026-10-11 (Sun)_

## Status
**Planning phase, explorations done (2026-10-11 evening).**
- D19 (archive as gap filler) accepted.
- Targets agreed: 1h/3h = new alert + its duration; 24h = count, hours under alert, and timing. Night-alert probability is used as a feature.
- Spatial comparison (D16 results): the raion model with disaggregation wins at raion level; the oblast model wins at oblast level.
- Artillery check done (D20). Hole check done (D19 follow-up). Yellow/red numbers ready (D21).
- @air_alert_ua full scrape running: 4 parallel id ranges in `data/raw/telegram/air_alert_ua/`, ~7–8 h total, resumable. @war_monitor fully scraped. No modelling code yet.

## What exists
- `CLAUDE.md`: rules, including the no-leakage protocol and the working agreement (ask before acting, explain everything)
- `decisions.md`: decisions D1–D21
- `tasks.md`: phased task list with priorities for the deadline
- `Project-State.md`: this file
- `requirements.txt` + `.venv/` (local only): Python 3.13 with pandas, numpy, scikit-learn, LightGBM, requests, bs4, lxml, matplotlib, pyarrow, pytest
- `scripts/scrape_telegram.py`: scraper for public Telegram channels → `data/raw/telegram/<channel>.jsonl` (gitignored)

## Facts established so far
Pinned versions used in the explorations:
- Vadimkin `bf0c323c` (2026-10-11 04:50 UTC)
- JustJimer archive `7abc556b` (2026-10-11 10:07 UTC)

**Volunteer dataset** (`datasets/volunteer_data_en.csv`)
- 115,989 alerts, 2022-02-25 → 2026-10-11, oblast level, 25 regions (incl. Kyiv City and Luhanska).
- About 5% of the alerts are `naive` (the end time is guessed as start + 30 min).
- Alerts per month keep growing:

  | Month | Alerts |
  |---|---|
  | 2025-09 | 2,167 |
  | 2026-03 | 3,350 |
  | 2026-08 | 3,916 |
  | 2026-09 | 4,438 |

  This matches the new daytime drone tactic (D7).

**Official dataset** (`datasets/official_data_en.csv`)
- 299,275 alerts, 2022-03-15 → 2026-09-07. It seems to have stopped updating about 5 weeks ago.
- Levels: oblast 130k, raion 132k, hromada 37k.

**What neither dataset has**
- No threat-type column (drone/missile).
- No permanent sirens (Luhansk since 2022-04-04, Crimea).

**Telegram @war_monitor** (checked 2026-10-11)
- The public preview works and reaches the full history: post #1980 is from 2022-08-28; the newest post, #47555, from 2026-10-11.
- Posts are short, real-time, in Ukrainian. They carry:
  - the threat type: drones "БпЛА", jet drones "реактив", "Циркон", ballistic "балістика" / `🟣`, all clear "Відбій" / `⚪️`;
  - places (oblast, city, raion names) and directions ("вектор", "курс");
  - counts ("13х БпЛА");
  - daily situation summaries ("Обстановка станом на 00:00"): strategic aviation, missile carriers at sea. These could help predict massive night attacks.
- Caveats:
  - The channel is somewhat Kyiv-centric.
  - It has "technical works" gaps (e.g. 2026-10-10/11).
  - Posts can be edited (we record an `edited` flag).
- **Full scrape done:** 46,492 posts, #1 (2022-04-25) → #47555 (2026-10-11). 5.6% are edited; about 1k post numbers are missing (deleted). The channel didn't exist before 2022-04-25.

**@air_alert_ua** (the source of the official dataset) stopped posting on 2026-09-07 (see D18). The cause: the yellow/red reform changed the message format on 2026-09-06.

**JustJimer archive** (alerts.in.ua): raion-level data with yellow/red and air_raid vs artillery, complete from 2026-09-06 12:00 UTC to today. It matches the official data 97% on the overlap. **This fills the gap** (D19).

## Open questions for the user
1. Who creates the Netlify site (your account)? When?
2. alerts.in.ua: the API key isn't here yet. Once it arrives, approve the site and give the key as an environment variable, never in the repo.

## Answered
- D4 accepted. The other Proposed decisions get settled during implementation.
- Deadline: Monday 2026-10-12 23:59 **Kyiv time**.
- Git: work on a branch; on "merge in main" → push, PR, merge.
- Python libraries: installation approved.
- Telegram: option A (public web preview) approved, with t.me allowed.

## Latest results
None yet.

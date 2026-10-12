# Project State

_Last updated: 2026-10-11 (Sun)_

## Status (2026-10-12 morning)
**Tasks 1 and 2 of the overnight plan are done. Waiting for the user's review and the "go" for the final test run.**
- Data pipeline: `scripts/download_data.py` → `scripts/build_alert_table.py` → `scripts/build_panel.py` (outputs in `data/processed/`, parquet not in git).
- @air_alert_ua fully scraped. 99.99% of official rows labelled by message type; 22,273 artillery rows (7.4%) excluded.
- Leakage tests: 7 passing (`tests/test_leakage.py`).
- Validation: `scripts/validate_models.py` → `reports/validation.md`. The test period (from 2026-09-13) is untouched.
- New decisions D27–D35 are **Proposed**, waiting for review.
- Next: user review → final test run → JSON export → website (Netlify) → Telegram ablation.

## What exists
- `CLAUDE.md`: rules, including the no-leakage protocol and the working agreement (ask before acting, explain everything)
- `decisions.md`: decisions D1–D21
- `tasks.md`: phased task list with priorities for the deadline
- `Project-State.md`: this file
- `requirements.txt` + `.venv/` (local only): Python 3.13 with pandas, numpy, scikit-learn, LightGBM, requests, bs4, lxml, matplotlib, pyarrow, pytest
- `scripts/scrape_telegram.py`: scraper for public Telegram channels → `data/raw/telegram/` (gitignored); supports parallel id ranges
- `scripts/explore_spatial_options.py` + `reports/spatial_options.md`: oblast vs raion comparison (D16 results)
- `scripts/download_data.py`, `data/versions.json`: datasets at pinned commits (Vadimkin `bf0c323c`, JustJimer `7abc556b`)
- `src/alerts/` (sources, telegram, build, features) + `scripts/build_alert_table.py`, `scripts/build_panel.py`: the pipeline
- `tests/test_leakage.py`: leakage tests
- `scripts/validate_models.py`: walk-forward validation of all models
- Reports: `data_quality.md`, `air_alert_ua_messages.md`, `validation.md`, `validation_metrics.json`

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
2. alerts.in.ua API key: still pending. It's no longer blocking, thanks to the JustJimer archive.

## Answered
- D4 accepted. The other Proposed decisions get settled during implementation.
- Deadline: Monday 2026-10-12 23:59 **Kyiv time**.
- Git: work on a branch; on "merge in main" → push, PR, merge.
- Python libraries: installation approved.
- Telegram: option A (public web preview) approved, with t.me allowed.

## Latest results (validation, 4 weekly folds, Aug 16 – Sep 12 2026)
- New alert within 1h: LightGBM AUC 0.84 (raion) / 0.86 (oblast); skill vs the same-hour rule 0.18 / 0.21; well calibrated.
- New alert within 3h: AUC 0.85 / 0.86; skill 0.33 / 0.36.
- 24h timing blocks: AUC 0.80–0.86 (vs 0.72 for the simple rule).
- 24h count/hours and duration: barely better than persistence.
- Red given alert: the simple rule (raion red share 7d) AUC 0.82 beats the full models.

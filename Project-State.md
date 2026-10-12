# Project State

_Last updated: 2026-10-12, ~15:10 Kyiv (end of session 1)._ Deadline: **today 23:59 Kyiv**.

## Where we are
- **Data pipeline: done.** Official data (artillery and other non-air-raid rows removed via @air_alert_ua message labels) + JustJimer alerts.in.ua archive (from 2026-09-06 12:00 UTC, with yellow/red). 119 raions, 24 oblasts (Luhansk and Crimea excluded), 2022-02 → 2026-10-11.
- **Forecasting tables: done** (hourly per raion and oblast since 2022-03, leakage-safe, 9 leakage tests passing).
- **Validation and model selection: mostly done.** Accepted choices:
  - LightGBM;
  - history: raion = last 12 months, oblast = full history with recency weights (D40);
  - duration and 24h counts shown as ranges (D41);
  - yellow/red: the best on validation (currently the simple 7-day share rule);
  - Telegram (@war_monitor) not used (D44).
- **Still to choose:** timing hybrid (D45, Proposed); LightGBM tuning (not done).
- **Website: skeleton done** in `site/` on SAMPLE data (map, click panel, strips, heatmap, replay, quality, about). Real data export not done yet.
- **NOT done:** final test run (13 Sep – 11 Oct), "now" and week-ahead predictions, `scripts/export_site.py`, Netlify deploy, README.

## Data snapshots (all downloads complete)
- **In git (D15):** `data/telegram/*.jsonl.gz` and `data/labels/official_labels.parquet`. **Complete** downloads:
  - @war_monitor: 46,492 posts, 2022-04 → 2026-10-11;
  - @air_alert_ua: 338,360 posts, 2022-03 → 2026-09-07;
  - @kpszsu: 44,057 posts, 2025-08-31 → 2026-10-12;
  - @UkraineAlarmSignal: 45,875 posts, 2026-08-31 → 2026-10-12.
- **In a fresh container:**
  1. `bash scripts/restore_data.sh`;
  2. `python scripts/download_data.py --pin`;
  3. `PYTHONPATH=. python scripts/build_alert_table.py`;
  4. `PYTHONPATH=. python scripts/build_panel.py --start 2022-03-01`.

## How to run (from the repo root)
```
python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
python scripts/download_data.py --pin                         # pinned data versions (data/versions.json)
python scripts/scrape_telegram.py war_monitor --out data/raw/telegram/war_monitor.jsonl
# @air_alert_ua: 4 parallel id ranges, see decisions.md D18/D25 (~2.5 h)
PYTHONPATH=. python scripts/build_alert_table.py              # -> data/processed/alerts_*.parquet, reports/data_quality.md
PYTHONPATH=. python scripts/build_panel.py --start 2022-03-01 # -> panel_raion/oblast.parquet, red_events.parquet
PYTHONPATH=. python -m pytest -q tests/                       # leakage tests
PYTHONPATH=.:scripts python scripts/validate_models.py        # and compare_windows / compare_telegram / validate_timing / explore_weak_targets
PYTHONPATH=. python scripts/build_map.py                      # site/data/raions.geojson
python scripts/make_sample_site_data.py                       # SAMPLE json for the site (replace with export)
cd site && python3 -m http.server 8765                        # view the site
```
**Run heavy model jobs ONE AT A TIME** (4 cores; parallel LightGBM jobs slow down dramatically).

## Pinned data
- Vadimkin `bf0c323c` (2026-10-11 04:50 UTC).
- JustJimer archive `7abc556b` (2026-10-11 10:07 UTC; no newer commit at 13:35 Kyiv). Re-check before the final build (user request).
- @air_alert_ua: complete (338,360 posts, stopped 2026-09-07).
- @war_monitor: complete to 2026-10-11 (46,492 posts).

## Key results (validation, Aug 16 – Sep 12 2026; test untouched)
- New alert within 1h: AUC 0.85 (raion) / 0.87 (oblast); skill vs the same-hour rule 0.19 / 0.21; well calibrated.
- New alert within 3h: AUC 0.85 / 0.87; skill 0.33 / 0.37 (accepted history windows).
- Timing (3h Kyiv blocks): day 1 AUC 0.80 vs 0.76 for the pattern rule; days 3–7 no better than the pattern (D45).
- 24h count/hours: 8–10% smaller error than the 7-day average.
- Duration range (25–75%): covers 45% (ideal 50%) vs 41% for the simple rule.
- Red given alert: the simple rule (raion red share 7d) AUC 0.82, best so far.
- Telegram (@war_monitor): slightly worse on every target (D44).

## Reports
`reports/`: `data_quality.md`, `air_alert_ua_messages.md`, `spatial_options.md`, `validation.md`, `training_window.md`, `weak_targets.md`, `telegram_ablation.md`, `timing_validation.md`, `map_preview.png`, `site_preview_sample.png`.
Plain-English explanation of the whole method: **`docs/how_it_works.md`**.

## Open questions for the user
1. D45: accept the timing hybrid (model for days 1–2, pattern for days 3–7)?
2. Netlify: the user has an account; deploy together later today.

# Tasks

Deadline: **Mon 2026-10-12, 23:59 Kyiv**. Done items from earlier phases are summarised; details in `Project-State.md`.

## Done
- [x] Context files, git workflow, venv, approved-sites list
- [x] Data: Vadimkin + JustJimer archive (pinned); @air_alert_ua (full) and @war_monitor (full) scraped
- [x] Official rows labelled by message type; artillery / threat warnings excluded (D25, D28)
- [x] Holes rule (D29, refined); Lviv/Volyn volunteer quirk (D30); volunteer not used as patches
- [x] Raion + oblast alert tables; hourly forecasting panels since 2022-03; leakage tests (9 passing)
- [x] Validation of all targets; training window (D40); weak targets (D41); Telegram ablation (D44); timing model validation (D45)
- [x] Map shapes (`site/data/raions.geojson`, 0.34 MB, all 119 raions matched)
- [x] Website skeleton on SAMPLE data (map, click panel with 24h cells, week heatmap, week-ahead strip, history strip; replay; quality; about)
- [x] `docs/how_it_works.md`

## Next (in order)
1. [x] Telegram downloads @kpszsu (since 2025-09) and @UkraineAlarmSignal (since 2026-09) complete, in git
2. [ ] User decisions: D45 timing hybrid, D15 data in git
3. [ ] **LightGBM tuning**, time-boxed (~40 min, validation folds only), raion + oblast 3h
4. [ ] (if time) @kpszsu features → re-run `scripts/compare_telegram.py` with @kpszsu instead of @war_monitor
5. [ ] (if time) @UkraineAlarmSignal cross-check of the archive (holes, Lviv/Volyn, yellow/red)
6. [ ] Re-check the JustJimer repo for new data; if any → `download_data.py`, rebuild tables/panels
7. [ ] **Final choice table** → user sign-off
8. [ ] **Final test run** 13 Sep – 11 Oct (main models; red: train Sep 6–26, test Sep 27+), hourly predictions for the replay and the history strip
9. [ ] Retrain on all data → "now" + week-ahead predictions
10. [ ] `scripts/export_site.py` → `site/data/{meta,now,week,history,replay,metrics}.json` (same format as the sample)
11. [ ] Site: real data, quality page numbers (incl. with/without Telegram), screenshots → user
12. [ ] Netlify deploy (with the user; `netlify.toml` publishes `site/`)
13. [ ] README, final explanation, merge into main

## Later / optional
- Artillery as a separate small product for Nikopol / Marhanets (D39 option b)
- Neighbouring-district inputs; live hourly updates; Ukrainian language

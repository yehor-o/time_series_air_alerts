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
1. [x] Finish the Telegram downloads (@kpszsu, @UkraineAlarmSignal)
2. [x] D45 decided: blend model/pattern (user, after `reports/timing_variants.md`); implemented in `src/alerts/timing.py`
2b. [x] Committed Telegram snapshots refreshed with the complete @kpszsu and @UkraineAlarmSignal downloads
3. [x] **LightGBM tuning** done: small gains, D47 Proposed (`reports/tuning.md`)
4. [x] @kpszsu features: NOT used, worse on probability targets (D44, `reports/kpszsu_ablation.md`)

5. [ ] (if time) @UkraineAlarmSignal cross-check of the archive (holes, Lviv/Volyn, yellow/red)
6. [x] Re-checked: both repos have newer commits; user chose to keep the pins
7. [x] **Final choice table** signed off (D47 accepted)
8. [x] **Final test run** done (`reports/test_results.md`, `test_metrics.json`, hourly predictions in `reports/test_predictions_*.parquet`)
9. [ ] Retrain on all data → "now" + week-ahead predictions
10. [ ] `scripts/export_site.py` → `site/data/{meta,now,week,history,replay,metrics}.json` (same format as the sample)
11. [ ] Site: real data, quality page numbers (incl. with/without Telegram), screenshots → user
12. [ ] Netlify deploy (with the user; `netlify.toml` publishes `site/`)
13. [ ] README, final explanation, merge into main

## Later / optional
- Artillery as a separate small product for Nikopol / Marhanets (D39 option b)
- Neighbouring-district inputs; live hourly updates; Ukrainian language

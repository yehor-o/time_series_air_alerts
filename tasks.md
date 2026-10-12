# Tasks

The deadline version (Mon 2026-10-12, 23:59 Kyiv) is done and live: https://air-alert-forecast-ua.netlify.app
Details in `Project-State.md`; plans for the next steps in `docs/next_steps.md`.

## Done
- [x] Context files, git workflow, venv, approved-sites list
- [x] Data: Vadimkin + JustJimer archive (pinned); Telegram channels scraped and committed as snapshots (D15)
- [x] Official rows labelled by message type; non-air-raid warnings excluded (D25, D28); holes rule (D29); volunteer quirk (D30)
- [x] Raion + oblast alert tables; hourly forecasting tables since 2022-03; leakage tests (13 passing)
- [x] Validation: models, training window (D40), weak targets (D41), Telegram @war_monitor and @kpszsu (D44), timing blend (D45)
- [x] LightGBM tuning (D47)
- [x] Final choice table signed off; **final test run** (`reports/test_results.md`); no changes after the test (D48)
- [x] Live forecast + site export; 24 h ranges (D49); data refresh (D50)
- [x] Website: map, replay, Forecast check, "How good is it?" with model-comparison charts, About; Ukrainian version
- [x] Netlify deploy; README; `docs/how_it_works.md`
- [x] **Live hourly forecasts** via the alerts.in.ua API + GitHub Actions (D51, D52); twice-monthly retraining via PR
- [x] Editorial Dark design; Major-cities card; "under alert now"; clearer Forecast check

## Next (planned, need approval; see `docs/next_steps.md`)
1. [ ] **Task 5: keep the repo small** (D54): live data on a `live-data` branch + Netlify build hook; models as GitHub Releases; archive cleanup (~1.5–2 h)
2. [ ] **Task 3: faster hourly runs** (D53): rolling API refresh, validated offline first (~2 h; after task 5)
3. [ ] **Task 4: neighbouring-district inputs** (D55): ~5 h of work + 2–4 weeks of new data for a fair test

## Open items
- [ ] User: review the Ukrainian texts
- [ ] Watch the first scheduled hourly runs

## Later / optional
- @UkraineAlarmSignal cross-check of the archive (holes, Lviv/Volyn, D30)
- Artillery warnings as a separate small product for Nikopol / Marhanets (D39 option b)
- Phone layout (the site is desktop-only, D43)

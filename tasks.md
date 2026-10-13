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
- [x] Site QA (session 3) and website-only fixes (D56): under-alert stripes + continuous alerts, outlook vs hourly labels,
      history-strip gaps, About page, red-tile evidence
- [x] Live-run reliability (D57, 2026-10-13): cron skipped ~11 of 12 hourly slots; added extra cron slots, a self-dispatch
      chain and a same-hour skip. Outside hourly trigger (cron-job.org + GitHub token) not set up: needs the user's account

- [ ] **Hourly updates paused** (Netlify credits): serve `site/data` without a Netlify deploy per hour, then turn the
      schedule back on (needs the user's decision)

- [ ] **Bug D58: local alerts promoted to whole districts** (Kharkivskyi, Nikopolskyi; "continuous alert 7+ days").
      Fix proposed in D58, waiting for the user's approval; then rebuild, retrain, validate (not in main yet)

## Next (planned, need approval; see `docs/next_steps.md`)
1. [ ] **Task 5: keep the repo small** (D54): live data on a `live-data` branch + Netlify build hook; models as GitHub Releases; archive cleanup (~1.5–2 h)
2. [ ] **Task 3: faster hourly runs** (D53): rolling API refresh, validated offline first (~2 h; after task 5)
3. [ ] **Task 4: neighbouring-district inputs** (D55): ~5 h of work + 2–4 weeks of new data for a fair test

## Open from the site QA (2026-10-12, not started; numbers as in the QA report)
- [ ] 2b. Stitch the hourly 1 h / 3 h forecast into the outlook blocks that overlap the next 3 hours (pipeline, decision needed;
      check both versions on the Forecast check for 2 weeks)
- [ ] 7b. Red share with shrinkage toward the national share, k chosen on 13–26 Sep (changes D35; pipeline + data rebuild)
- [ ] 5. "Next 1 h" window is partly over when published (show clock times; faster runs, task 3)
- [ ] 6. Staleness banner if the forecast is more than ~2 h old
- [ ] 8. Forecast check: label partly checked forecasts; explain empty tiles; "data up to" mismatch with the header
- [ ] 9. Netlify badge overlaps the bottom right (Netlify setting); cities card covers the south-east; block picker covers the north
- [ ] 10–15. Polish: "Kyiv City, Kyiv City"; UA tabs wrap at 1280 px; colour ramp contrast and week-strip 35% floor;
      district search / keyboard access; phone layout (D43); map re-fit on resize

## Open items
- [ ] User: review the Ukrainian texts (incl. the new About and panel texts)
- [ ] Watch the scheduled hourly runs (none had started by 20:35 UTC on 12 Oct)

## Later / optional
- @UkraineAlarmSignal cross-check of the archive (holes, Lviv/Volyn, D30)
- Artillery warnings as a separate small product for Nikopol / Marhanets (D39 option b)
- Phone layout (the site is desktop-only, D43)

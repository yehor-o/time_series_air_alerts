# Tasks

Deadline: **Mon 2026-10-12, 23:59 Kyiv time**. Priority: **P0** = must have for the deadline, **P1** = should have, **P2** = if time allows.
Every task ends with a short explanation for the user of what was done and why.

## Phase 0 — Setup
- [x] Agree on the task understanding with the user
- [x] Inspect the Vadimkin dataset (structure, coverage, freshness)
- [x] Write the context files (CLAUDE.md, Project-State.md, tasks.md, decisions.md)
- [x] User reviewed decisions: D4 accepted; the others will be settled during implementation
- [x] Python venv + libraries installed (`requirements.txt`), `.gitignore`
- [ ] **P0** Repo skeleton (`src/`, `notebooks/`, `site/`, `reports/`)
- [ ] **P0** Create `main` on GitHub (the repo is empty) and set up the branch → PR → merge workflow
- [ ] **P0** `scripts/download_data.py`: download the datasets and record the commit hash

## Phase 1 — Data understanding (EDA)
- [ ] **P0** Load and clean the volunteer data: parse UTC times, handle `naive` rows, overlapping and duplicate alerts, drop Luhanska
- [ ] **P0** Cross-check volunteer vs official data on the overlap. Confirm that the official data really stops at 2026-09-07.
- [ ] **P0** EDA plots: alerts per day over time; hour-of-day profile by year (to show the daytime-drone shift); per-oblast rates; alert durations
- [ ] **P1** Short EDA write-up for the user (plain English)

## Phase 2 — Problem framing and leakage-safe dataset
- [ ] **P0** Build the hourly panel: one row per (oblast, issue time t)
- [ ] **P0** Targets: `y_1h, y_3h, y_24h` = a new alert starts in (t, t+h]
- [ ] **P0** Features, all computed from data before t only:
  - alert currently active, and minutes since its start
  - time since the last alert ended
  - number of alerts and alert-minutes in the last 1h/3h/6h/24h/7d
  - the same counts for neighbouring oblasts and for the whole country
  - hour-of-day rate over the last 7/14 days (the daytime-regime signal)
  - calendar: Kyiv hour, weekday
- [ ] **P0** Leakage unit tests: deleting future data must not change any feature
- [ ] **P0** Chronological splits: walk-forward validation folds + 4-week test (D6)

## Phase 3 — Models and evaluation
- [ ] **P0** Baselines: climatology, recent rate, persistence
- [ ] **P0** Logistic regression
- [ ] **P0** LightGBM
- [ ] **P1** Tune the training-window length and recency weighting (D7)
- [ ] **P0** Evaluation report: Brier, log-loss, ROC-AUC, PR-AUC, calibration; per horizon; day vs night; per oblast
- [ ] **P0** Final single run on the test period. Export predictions to JSON for the site.
- [ ] **P1** Feature importance and explanation of how the model decides (for the user)
- [ ] **P2** A duration/hazard model or a neural sequence model

## Phase 4 — Website (Netlify)
- [ ] **P0** Static site: oblast map coloured by forecast probability, with a horizon switch (1h/3h/24h)
- [ ] **P0** Model comparison page: metrics table and calibration chart
- [ ] **P1** Alert history view per oblast; actual vs predicted on the test period
- [ ] **P0** Deploy to Netlify *(needs the user's Netlify account and approval)*
- [ ] **P2** Live hourly updates via GitHub Action
- [ ] **P2** Ukrainian translation

## Phase 5 — Telegram (@war_monitor) — after Phase 3 works
- [x] Decide the access method → public web preview (D10); full history since 2022 is reachable
- [x] Scraper `scripts/scrape_telegram.py` (pagination, retries, edited flag)
- [ ] **P1** Collect messages since 2024-01-01 *(running)*
- [ ] **P1** Data audit: posts per day, gaps / "technical works" periods, share of edited posts, which oblasts and cities get mentioned
- [ ] **P1** Keyword classifier: drone / jet drone / missile / ballistic / KAB / strategic aviation / all-clear / daily summary (D14)
- [ ] **P1** Features: message counts in the last 1h/3h/6h; keywords (e.g. "massive attack", "shahed", "missile", "tu-95", oblast names); evening warnings about a night attack
- [ ] **P1** Ablation: the same model with vs without Telegram features, on the same splits
- [ ] **P2** Threat-type target (yellow/red) inferred from Telegram (D14)

## Phase 5b — District (raion) level (D13, brainstorm first)
- [ ] **P2** Brainstorm with the user: hierarchical oblast→raion vs a separate raion model
- [ ] **P2** Check the official raion data, Dec 2025 → 2026-09-07 (coverage, number of raions)
- [ ] **P2** alerts.in.ua API to fill the gap since 2026-09-07 *(blocked: no API key yet; site needs approval)*

## Phase 6 — Wrap-up
- [ ] **P0** README: what the project does, how to run it, results
- [ ] **P0** Final explanation session with the user: how the model predicts, what the metrics mean, limitations

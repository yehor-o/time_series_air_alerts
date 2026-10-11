# Tasks

Deadline: **Mon 2026-10-12, 23:59 Kyiv time**. Priority: **P0** = must have for the deadline, **P1** = should have, **P2** = if time allows.
Every task ends with a short explanation for the user of what was done and why.

## Phase 0 — Setup ✅
- [x] Agree on the task understanding with the user
- [x] Context files (CLAUDE.md, Project-State.md, tasks.md, decisions.md)
- [x] Python venv + libraries (`requirements.txt`), `.gitignore`
- [x] `main` branch on GitHub + branch → PR → merge workflow

## Phase 1 — Data sources and checks ✅ (mostly)
- [x] Vadimkin dataset inspected: the official part ends 2026-09-07; the volunteer part is up to date
- [x] Root cause: the yellow/red reform changed the @air_alert_ua message format (D18, D19)
- [x] Gap filler found and validated: JustJimer alerts.in.ua archive, 97% match on the overlap (D19)
- [x] Hole check of the archive: one real hole on 2026-10-07; Lviv/Volyn mismatch open (D19 follow-up)
- [x] Artillery check: about 10% of the official rows checked so far are artillery threats, all hromada level (D20)
- [x] Spatial options compared: raion model + oblast model (D16 results, D22)
- [x] First yellow/red statistics (D21)
- [x] @war_monitor full history scraped (46,492 posts)
- [ ] **P0** @air_alert_ua full history scrape *(running: 4 parallel id ranges, about 50% done)*
- [ ] **P0** Label every official row by its message type; keep only air raids (D25)
- [ ] **P0** Investigate the Lviv/Volyn volunteer-vs-archive mismatch and report to the user (D26)
- [ ] **P0** Verify volunteer gap fills against @air_alert_ua / @war_monitor before using them (D26)

## Phase 2 — Data pipeline (approved)
- [ ] **P0** `scripts/download_data.py`: Vadimkin + JustJimer archive at pinned commits
- [ ] **P0** Clean alert table, raion level:
  - official air raids only;
  - plus the archive from 2026-09-06 12:00 UTC;
  - plus verified volunteer patches;
  - a `source` column and a yellow/red `level` column (from the reform on).
- [ ] **P0** Disaggregation: oblast-wide alerts → every raion; merge overlapping alerts per unit
- [ ] **P0** Oblast table: union of its raions (for the oblast model)
- [ ] **P1** EDA charts with plain-English notes: alerts over time, the daytime shift, per-oblast and per-raion rates, durations

## Phase 3 — Forecasting table + leakage tests (approved)
- [ ] **P0** Hourly panel per raion and per oblast (issue time t = every hour)
- [ ] **P0** Targets (D23):
  - 1h/3h: new alert + its duration;
  - 24h: count, hours under alert, timing;
  - red share given an alert (D24).
- [ ] **P0** Features:
  - current state;
  - recent counts (unit, oblast, nation);
  - hour-of-day rates (the daytime-drone regime);
  - night-alert probability;
  - recent yellow/red levels;
  - calendar (Kyiv time).
- [ ] **P0** Leakage unit tests (deleting all data after t must not change any feature at t)
- [ ] **P0** Chronological splits: walk-forward validation folds; test = the last 4 weeks (from about 2026-09-13), used once

## Phase 4 — Models and evaluation (approved)
- [ ] **P0** Baselines: same hour last 14 days, persistence
- [ ] **P0** Logistic regression, LightGBM (raion and oblast, per horizon)
- [ ] **P0** Duration model (1h/3h) and count/hours/timing models (24h)
- [ ] **P0** Yellow/red model (reform period only)
- [ ] **P1** Tune the training-window length and recency weighting (D7)
- [ ] **P0** Evaluation report: Brier, log-loss, AUC, calibration; day vs night; per oblast
- [ ] **P0** One final run on the test period; export JSON for the site

## Phase 5 — Website (Netlify)
- [ ] **P0** Static English site: raion map + oblast view, horizon switch, "chance of alert" and "chance it's red"
- [ ] **P0** Model comparison page (metrics, calibration)
- [ ] **P0** Credits: Vadimkin dataset, JustJimer archive (alerts.in.ua), @war_monitor, @air_alert_ua
- [ ] **P0** Deploy to Netlify *(needs the user's Netlify account)*
- [ ] **P2** Live hourly updates; Ukrainian translation

## Phase 6 — Telegram features
- [ ] **P1** @war_monitor audit and keyword classifier (drone / jet drone / ballistic / missile / KAB / strategic aviation / all-clear / summary)
- [ ] **P1** Drone-threat messages from @air_alert_ua
- [ ] **P1** Ablation: the same models with vs without Telegram features, on the same splits

## Phase 7 — Wrap-up
- [ ] **P0** README: what the project does, how to run it, results, credits
- [ ] **P0** Final explanation session with the user

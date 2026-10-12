# Final choice table (for the user's sign-off before the final test run)

All numbers are **validation** results (weeks before 2026-09-13). The test period (13 Sep – 11 Oct 2026) has not been
touched. Pinned data: Vadimkin `bf0c323c`, JustJimer `7abc556b`. Skill = how much smaller the error is than the simple rule
named in the row (0 = no better).

| Target | Chosen method | History used | Validation result (raion / oblast) | vs simple rule | Decision |
|---|---|---|---|---|---|
| New alert within 1h | LightGBM classifier, tuned settings (D47) | raion: last 12 months; oblast: full history, recency-weighted (half-life 12 months) | AUC 0.85 / 0.87; well calibrated | skill 0.188 / 0.218 after tuning vs "same hour, last 14 days" | D35, D40, D47 |
| New alert within 3h | LightGBM classifier, tuned settings (D47) | same | AUC 0.85 / 0.87; well calibrated | skill 0.333 / 0.371 after tuning (0.326 / 0.366 before) | D35, D40, D47 |
| Duration of that alert | LightGBM quantile models, shown as "usually X–Y min" (25th–75th percentile) | same | range contains the true duration 45% of the time (ideal 50%) | rule (last 10 alerts): 41% | D41 |
| Next 24h: number of alerts, hours under alert | LightGBM regressors, shown as ranges | same | count MAE 1.48 / 1.64 alerts; hours MAE 1.91 / 2.02 h | 8–10% smaller error than the 7-day average | D41 |
| When: 3-hour Kyiv blocks, next 7 days | **Blend**: w × LightGBM timing model + (1 − w) × pattern rule, w = 1 − lead/72 h | raion 12 months; oblast 24 months, recency-weighted | day 1 AUC 0.80 / 0.80; Brier skill over all 56 blocks +0.016 / +0.024 | pattern rule (share of last 14 days) | D42, **D45** |
| Red vs yellow (if an alert starts) | Simple rule: the raion's red share over the last 7 days | reform period only (from 2026-09-06) | AUC 0.82 | logistic / LightGBM were not better (0.82 / 0.80) | D24, D32, D35 |
| Telegram inputs | **None.** @war_monitor and @kpszsu both made the main targets worse | — | see `telegram_ablation.md`, `kpszsu_ablation.md` | — | D44 |

## What gets frozen for the final test run
- Feature lists: `BASE_FEATS` (+ `PARENT_FEATS` for raions), `TIMING_EXTRA` (`scripts/validate_models.py`, `src/alerts/timing.py`).
- LightGBM settings for the 1h/3h classifiers (D47, tuned on validation): raion 31 leaves, min 500 rows per leaf, learning rate 0.03 × 700 trees, 60% of inputs per tree; oblast the same with min 1000 rows per leaf.
- All other LightGBM models (duration, 24h count/hours, timing): 400 trees, learning rate 0.05, 63 leaves, min 500 rows per leaf (D34).
- Training histories as above; fixed random seed.
- The test is run once: main models train on everything before 2026-09-13; red/yellow trains on 6–26 Sep and is tested from 27 Sep.

## Open, not blocking
- @UkraineAlarmSignal: only ~6 weeks of history, so used as a cross-check of the archive, not as a model input.

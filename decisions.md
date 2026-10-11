# Decisions Log

Each entry has: context, decision, alternatives, consequences, and status.
**Status:** `Accepted` = agreed with the user. `Proposed` = Claude's suggestion that is waiting for the user's approval.

---

## D1. Data source: Vadimkin GitHub dataset — Accepted
**Context:** The alerts.in.ua API needs a token, which is given on request. We have no time to wait for one.
**Decision:** Use https://github.com/Vadimkin/ukrainian-air-raid-sirens-dataset. It is updated daily by a GitHub Action, and all times are in UTC.
It contains two datasets:
- **Volunteer** (`volunteer_data_en.csv`; source: eTryvoga channel): 2022-02-25 → present (last row 2026-10-11 04:36 UTC when inspected). **Oblast level only.** Columns: `region, started_at, finished_at, naive`. About 5% of rows are `naive=True`: the end of the alert was unknown, so it was set to start + 30 min.
- **Official** (`official_data_en.csv`): 2022-03-15 → **2026-09-07** (it looks like it stopped updating; to be verified). Columns: `oblast, raion, hromada, level, started_at, finished_at, source`. Levels are oblast, raion and hromada. Since Dec 2025 alerts are mostly at raion level.
**Alternatives:** alerts.in.ua API (needs a token), ukrainealarm.com API (needs a key), scraping the official Telegram channel ourselves (costs too much time).
**Consequences:** No live API is needed for the deadline version. The data contains **no alert type** (drone vs missile, i.e. yellow vs red); see D5.

## D2. Primary dataset = volunteer; official = secondary — Proposed
**Reason:** The volunteer data is up to date (needed for "evaluate on the latest period"). It also uses one consistent spatial level (oblast) for the whole war, which avoids the oblast→raion change in the official data.
**Use of official data:** cross-check the volunteer data on the overlapping period. Possibly a raion-level extension later.

## D3. Spatial unit = oblast (25 units incl. Kyiv City) — Proposed
**Context:** Alerts moved from oblast level to raion/hromada level (mostly from Dec 2025). Old and new alerts are hard to compare directly.
**Decision:** Forecast at oblast level. In the official data, "any raion/hromada alert in the oblast" counts as an oblast alert.
**Exclusions:** **Luhanska oblast** has had a permanent siren since 2022-04-04, so there is nothing to forecast there. Exclude it. Crimea has a permanent siren too, but it is not in the data.
**Alternatives:** raion level (more detailed, but only consistent from Dec 2025, which leaves too little history and the official data is stale).

## D4. Forecast target and issue times — Proposed
- A forecast is issued **every hour on the hour** (t = HH:00 UTC), for every oblast.
- **Primary target:** `y_h(t) = 1` if **a new alert starts** in oblast r during (t, t+h], for h ∈ {1h, 3h, 24h}.
- **Why "starts" rather than "is active":** if an alert is already active at t, "active within the next hour" is almost always true. That would make the task trivially easy and inflate the scores. Whether an alert is currently active is still used as an input feature.
- **Secondary (if time allows):** "alert active at any moment in (t, t+h]". It's closer to what a person on the street cares about.
- **Output:** a probability between 0 and 1, not just yes/no.

## D5. Alert type (yellow = drones, red = missiles) — Accepted as out of scope for v1
**Context:** Alert levels by threat type were introduced recently. Neither dataset has a type column.
**Decision:** v1 forecasts "any alert". Threat type could later be inferred from Telegram text (e.g. @war_monitor messages that mention "shahed" or "missile"). That would be a stretch goal.

## D6. Evaluation protocol — Proposed
- **Test set = the last 4 weeks** of available data (about 2026-09-13 → the dataset commit date). It is evaluated **once**, at the end.
- **Validation:** rolling-origin (walk-forward). For example, 4 weekly folds right before the test period. For each fold we train on everything before it and predict that week.
- **Metrics:**
  - Brier score: the mean squared error of the probabilities.
  - Log-loss.
  - ROC-AUC and PR-AUC: how well alerts are ranked above non-alerts.
  - Calibration plot: "when we say 30%, does it happen 30% of the time?".
  - Every metric is reported per horizon and also per time of day (day vs night).
- **Baselines every model must beat:**
  1. Climatology: the oblast's historical rate for this hour of the day.
  2. Recent rate: the oblast's rate over the last 7 days for this hour of the day.
  3. Persistence: "same as the last h hours".

## D7. Regime change: daytime drone attrition tactic — Accepted (as a requirement)
**Context:** Recently Russia launches a few drones at a time throughout the day (about 100–200 per day) to wear down people and air defence. This makes daytime alerts much more frequent. The data supports it: monthly alert counts rose from about 2.2k (Sep 2025) to 4.4k (Sep 2026).
**Consequences:**
- Old data describes a different "regime". Models must adapt by:
  - using **recent-window features** (last 1/3/7/14 days, split by hour of day);
  - **training-window length** as a tuned choice (all history vs last N months);
  - possibly **recency weighting** of training samples.
- Evaluation is reported separately for **daytime vs nighttime**, so we can see whether the model captures the new daytime pattern.

## D8. Time zones — Proposed
Store all times in UTC (as in the source). Compute calendar features (hour, weekday) in Europe/Kyiv local time, because people and attack patterns follow local time.

## D9. Models to compare — Accepted (the list itself is Proposed)
Accepted principle: test several models and choose the best on validation.
Proposed list, from simple to complex:
1. Baselines (D6).
2. Logistic regression on engineered features: simple and explainable.
3. LightGBM (gradient-boosted trees): usually the strongest on tabular features.
4. Optional, if time allows: a duration/hazard model or a small neural sequence model.

One model per horizon (1h, 3h, 24h), shared across oblasts, with the oblast as a feature.

## D10. Telegram data (@war_monitor) — Accepted (as a later phase, with ablation)
- This happens after the alert-only models work.
- **It must be evaluated as an ablation:** the same model and same splits, **with vs without** Telegram features, and the difference is reported.
- Only messages with publication time < t are used.
- **Access method is still undecided and needs the user's approval.** Options:
  - the public web preview `t.me/s/war_monitor` (no account, limited history);
  - Telethon (needs the user's Telegram API credentials).
- Telegram data must cover the training period, not only the test period. Otherwise the model can't learn from it.

## D11. Website — Accepted
- A static site in English, hosted on **Netlify**.
- It shows a map of Ukraine (oblasts) with forecast probabilities, alert history and the model evaluation results.
- Data comes from precomputed JSON files in the repo.
- A live, hourly updated version (scheduled GitHub Action) is postponed to "if time allows". Ukrainian translation is also "if time allows".

## D12. Raw data storage — Proposed
Do not commit the raw CSVs (the whole cloned dataset repo is about 130 MB). A script `scripts/download_data.py` downloads them into `data/raw/`, which is gitignored. The script records the dataset commit hash so that every result can be reproduced.

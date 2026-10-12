# How our forecasting works (plain English)

Written for the project owner. Updated as the project changes; the decisions behind each point are in `decisions.md`.

## 1. The question we answer

Every hour, for every district (raion) and every oblast:

> "Given everything known up to now, how likely is a **new** air raid alert to start here in the next hour? In the next 3 hours?"

Around it, we also estimate:
- how long such an alert would last;
- how many alerts and how many hours under alert to expect in the next 24 hours;
- **when**: the chance of a new alert in each 3-hour Kyiv-time block (00–03, 03–06, …, 21–24) of the next 7 days;
- whether an alert is likely to be **red** (missiles, ballistic, massed attack) or **yellow** (drones). Levels exist only since 6 Sep 2026.

## 2. The data, in one table

All alerts (official data until 7 Sep 2026, then the alerts.in.ua archive) are turned into **one row per district per hour**, about 4.8 million rows since March 2022. Each row has two parts:
- **inputs**: what was known at that hour (section 3);
- **answers**: what happened afterwards, e.g. did a new alert start within 1h or 3h, how long it lasted, how many alerts came in the next 24h.

The model learns the link between inputs and answers from millions of past rows.

**The no-leakage rule.** Inputs only use information from **before** the forecast moment.
- An alert still running at that moment is known only as "started, still active"; its end is not used.
- Automated tests (`tests/test_leakage.py`) check this. If you delete all data after time t, every input at t must stay exactly the same.

## 3. What the model sees (inputs)

| Group | Inputs | In plain words |
|---|---|---|
| This district now | alert active?; hours since the last alert started; hours since it ended | "Is something happening here right now?" |
| Recent activity | new alerts in the last 1, 3, 6, 24 h and 7 days; hours under alert in the last 3 h, 24 h, 7 days | "How busy has it been?" |
| Habits | share of the last 7 and 14 days with a new alert at this clock hour; share of the last 14 nights / days with any alert | "Is this a typical attack hour here?" (captures the daytime-drone shift) |
| Typical length | median duration of this district's last 10 alerts | used for duration ranges |
| Its oblast | share of the oblast's districts under alert now; new alerts in the oblast in the last 1, 3, 24 h | "Are neighbours under alert?" |
| Whole country | share of all districts under alert now; new alerts nationwide in the last 1, 3, 24 h | "Is a big attack going on?" |
| Calendar | hour of day, weekday (Kyiv time); which oblast | regional and daily patterns |
| Timing model only | how far ahead the block is; its clock block and weekday; share of the last 14 days (and last 4 same weekdays) with a new alert in that block, for the district, its oblast and the country | "Which hours of the coming days are usually dangerous here?" |
| Telegram (tested) | @war_monitor posts about drones, missiles and guided bombs in the last 3, 6, 24 h; drone numbers written in posts; strategic aviation active; posts naming the oblast; channel silence | "What kind of threat is in the air?" Used only if it wins on validation (see section 7) |

## 4. The model: LightGBM

LightGBM is a chain of small **decision trees**.
- One tree is a flowchart of yes/no questions, e.g. "Is the district under alert now? → More than 3 new alerts in the oblast in the last 3 h? → Between 01:00 and 05:00?". Each end of the flowchart gives a probability learned from history.
- The model builds hundreds of trees **one after another**, each correcting the mistakes of the ones before. The final forecast combines all of them.
- **One model serves all districts.** It knows which oblast a row belongs to, so it can learn regional differences.

Which model is used for what:
- **New alert within 1h / 3h:** LightGBM classifier ("yes/no" with a probability).
- **Duration:** three LightGBM *quantile* models, giving the 25th, 50th and 75th percentile. The 25th–75th pair becomes "usually X–Y min".
- **Count and hours in the next 24 h:** LightGBM regressors, shown as ranges.
- **Timing (7 days × 8 blocks):** one LightGBM classifier on rows of (forecast time, future block). The week-ahead number is a **blend** with the simple pattern rule: `w × model + (1 − w) × pattern`, where `w` falls in a straight line from 1 (right now) to 0 (3 days ahead). Near-term blocks use what is happening now; by day 3 the forecast is the district's typical habit. Chosen on validation (D45).
- **Red vs yellow:** the best of: the simple rule "this district's red share in the last 7 days", a logistic regression and LightGBM. Chosen on validation; today the simple rule wins.

## 5. How much history the models learn from

We tested this (`reports/training_window.md`):
- **District models: the last 12 months only.** Before mid-2025 alerts were oblast-wide, so all districts of an oblast had identical histories. That older data teaches the district model a pattern that no longer exists.
- **Oblast models: the full history (since April 2022), weighted towards recent data.**

### The recency-weighting formula

Every training row gets a weight, and the model counts that row's errors that many times:

```
weight = 0.5 ^ (age_in_days / 365)
```

"Age" is how long before the training cut-off the row's hour was. So the weight **halves every 12 months** (the "half-life"):

| Row from … before the cut-off | Weight | Meaning |
|---|---|---|
| yesterday | 1.00 | counts fully |
| 3 months | 0.84 | |
| 6 months | 0.71 | |
| 12 months | 0.50 | counts half |
| 2 years | 0.25 | counts a quarter |
| 4 years (spring 2022) | 0.06 | barely counts |

Compare "last 12 months only": weight 1 for anything younger than a year, **0** for anything older (a hard cut). Recency weighting is a soft version. Old situations still teach the model something (useful for rare events like massive attacks), but recent behaviour dominates. For oblasts it scored best (3h skill 0.366 vs 0.344 with the hard 12-month cut). For districts the hard cut won, because the old district rows are misleading copies, not just "older".

## 6. How we check it

- **Splits by time only.** Models train on the past and are scored on later weeks they never saw.
- **Validation:** 4 weekly "folds" (16 Aug – 12 Sep 2026). For each week, the model trains on everything before it and predicts that week. All choices (model type, inputs, history, settings) are made here.
- **Test:** 13 Sep – 11 Oct 2026, scored **once**, at the end. Yellow/red has its own test (27 Sep – 11 Oct) because levels only exist since 6 Sep.

## 7. How to read the scores

- **AUC:** pick a random hour when a new alert started and a random hour when none did. AUC is the chance the model gave the first one the higher probability. 0.5 = guessing, 1 = perfect.
- **Brier score:** the average of (forecast − what happened)². Lower is better. It punishes over-confident mistakes.
- **Skill:** how much smaller our Brier score is than a simple rule's. Usually the rule is "how often did an alert start at this clock hour on each of the last 14 days". 0 = no better; 0.3 = 30% smaller errors.
- **Calibration:** when we say 30%, does it happen about 30% of the time? Checked by grouping forecasts into bins.
- **MAE (mean absolute error):** the average size of the miss, in minutes, alerts or hours.
- **Coverage of a range:** how often the true value falls inside "usually X–Y". For a 25th–75th percentile range the ideal is 50%.
- **Telegram rule:** the version with @war_monitor inputs is used on the map only if it wins on the validation weeks. Both versions are shown on the "How good is it?" page.

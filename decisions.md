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

## D2. Base dataset = official; volunteer only fills gaps — Accepted (2026-10-11, user decision)
**Decision:** The **official** dataset is the base: oblast, raion and hromada levels. The **volunteer** dataset is used only where the official one has gaps:
- before 2022-03-15;
- outages;
- the period after the official file stops (2026-09-07 at last check).

The alerts.in.ua API will fill gaps once a key arrives.
**Finding (2026-10-11):** The official dataset is built from the public Telegram channel **@air_alert_ua** (official "Повітряна тривога" (Air Alert) channel), parsed by hashtags: 🔴 = alert, 🟢 = all clear. So we could fill the gap ourselves by scraping `t.me/s/air_alert_ua` and parsing it the same way. This keeps raion detail and the same definitions as the base. **Needs the user's approval:** a new channel.
**Risk:** the last 4 weeks (our test period) fall entirely inside the gap. The source we use to fill the gap therefore defines the test labels. It must match the official definition, so we check this on the overlap period.

## D3. Spatial unit = oblast (25 units incl. Kyiv City) — Superseded by D22
**Context:** Alerts moved from oblast level to raion/hromada level (mostly from Dec 2025). Old and new alerts are hard to compare directly.
**Decision:** Forecast at oblast level. In the official data, "any raion/hromada alert in the oblast" counts as an oblast alert.
**Exclusions:** **Luhanska oblast** has had a permanent siren since 2022-04-04, so there is nothing to forecast there. Exclude it. Crimea has a permanent siren too, but it is not in the data.
**Alternatives:** raion level (more detailed, but only consistent from Dec 2025, which leaves too little history and the official data is stale).

## D4. Forecast target and issue times — Accepted (2026-10-11)
- A forecast is issued **every hour on the hour** (t = HH:00 UTC), for every oblast.
- **Primary target:** `y_h(t) = 1` if **a new alert starts** in oblast r during (t, t+h], for h ∈ {1h, 3h, 24h}.
- **Why "starts" rather than "is active":** if an alert is already active at t, "active within the next hour" is almost always true. That would make the task trivially easy and inflate the scores. Whether an alert is currently active is still used as an input feature.
- **Secondary (if time allows):** "alert active at any moment in (t, t+h]". It's closer to what a person on the street cares about.
- **Output:** a probability between 0 and 1, not just yes/no.

## D5. Alert type (yellow = drones, red = missiles) — Superseded by D24
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
- **Access method: Accepted (2026-10-11).** Use the public web preview `t.me/s/war_monitor` (script `scripts/scrape_telegram.py`). Fallback: Telethon with the user's credentials.
  - Checked: the preview reaches the **full history**, back to 2022 (posts #1980 ≈ 2022-08-28, latest #47555 ≈ 2026-10-11), at 20 posts per page.
- **Leakage caveats specific to Telegram:**
  1. Posts can be **edited** after publication. The preview shows only the final text and an "edited" flag. Edited posts may contain information added later, so we can drop them, or measure how many there are and decide.
  2. Deleted posts are invisible, so we can't fully reconstruct "what was visible at time t".
  3. The channel has gaps ("technical works" posts, e.g. 2026-10-10/11). Features must handle a missing feed and must not read it as "calm".
- Telegram data must cover the training period, not only the test period. Otherwise the model can't learn from it.

## D11. Website — Accepted
- A static site in English, hosted on **Netlify**.
- It shows a map of Ukraine (oblasts) with forecast probabilities, alert history and the model evaluation results.
- Data comes from precomputed JSON files in the repo.
- A live, hourly updated version (scheduled GitHub Action) is postponed to "if time allows". Ukrainian translation is also "if time allows".

## D12. Raw data storage — Proposed
Do not commit the raw CSVs (the whole cloned dataset repo is about 130 MB). A script `scripts/download_data.py` downloads them into `data/raw/`, which is gitignored. The script records the dataset commit hash so that every result can be reproduced.

## D13. District (raion) level forecasts — Superseded by D22
**Context:** The user wants raion-level forecasts if possible. Raion alerts are the main mode since about Dec 2025.
**Data available:**
- **Official Vadimkin data:** raion and hromada rows through 2026-09-07. It stopped updating, which needs verifying.
- **Volunteer data:** oblast only, up to date.
- **alerts.in.ua API:** we have **no key yet**, and history is about the last month only.
**Ideas to evaluate:**
- (a) Model **oblast** first (main deliverable). Then add a raion model trained on official raion data, Dec 2025 → Sep 2026.
- (b) Fill the gap between 2026-09-07 and now with the alerts.in.ua API once a key arrives (needs approval of the site and the key).
- (c) A hierarchical approach: P(raion alert) = P(oblast alert) × P(raion | oblast alert), where the second factor comes from the raion data.
**Adaptation without a key:** the oblast pipeline doesn't depend on the API. Raion work starts only if time allows.

## D14. Threat type (yellow = drones, red = missiles) from Telegram — Proposed
**Context:** The alert datasets have no threat type. @war_monitor posts do: emojis and keywords, for example:
- `🟣` / "Загроза балістики" (ballistic threat), "спуск балістики" (ballistic missile descending)
- "Циркон" (Zircon)
- "БпЛА" (UAV / drone), "реактив" (jet-powered drone)
- "Стратегічна авіація" (strategic aviation), "ракетоносій" (missile carrier)
- `⚪️` "Відбій" (all clear)

**Idea:** a keyword-based classifier labels each post as drone / missile / ballistic / aviation-KAB / all-clear / summary. These labels feed (1) features and (2) later, possibly, an approximate threat-type target.

## D15. Telegram raw data storage — Proposed
Telegram history can change (edits, deletions), so a re-scrape is not perfectly reproducible. The raw JSONL lives in `data/raw/` (gitignored). A **processed, de-duplicated snapshot** with the scrape date will be committed (or published as a release asset if it is too big), so results can be reproduced.

## D16. Spatial unit: oblast vs raion — Resolved by D22
**Facts (official data, 2026-01-01 → 2026-09-06, Luhanska excluded):**
- Raion-level records rose from 7% (2025Q1) to 54% (2025Q3) to 92–94% (2026). Before mid-2025, almost all alerts were oblast-wide.
- On average an oblast has "any alert" 29.5% of the time, but the **whole** oblast is under alert only 12.1% of the time. When there is an alert, on average 72% of the oblast's raions are covered.
- Example: Kharkivska has "any alert" 86.6% of the time, the whole oblast 15.7%.
- Dnipropetrovska has "any alert" 99.9% of the time. This is likely driven by frontline hromada alerts (e.g. Nikopol), and possibly artillery-threat messages ("🔴 Загроза артобстрілу"). The Vadimkin parser treats every 🔴 message as an alert, so this needs checking.

**Options:**
- O1: oblast = any alert in any raion or hromada (union).
- O2: oblast-level share of raions under alert (a fraction target), or "majority of the oblast".
- O3: **raion-level target built for the whole war by disaggregation.** An oblast-wide alert before 2025 = an alert in every raion of that oblast. This keeps one target definition over time, and history at oblast level feeds in as input features. The problem: raion labels after 2026-09-07 exist only via the alerts.in.ua API (no key yet).
- O4: a hierarchical model: P(oblast) × P(raion | oblast).

## D17. 24h horizon reframing — Superseded by D23
**Fact:** Sep 1 → Oct 10, 2026 (volunteer data), **19 of 23 oblasts had at least one alert on ≥ 90% of days**. So "will there be an alert in the next 24h?" is almost always yes, and a model gets a high score just by saying yes.
**Proposal:** keep 1h and 3h as probabilities of a new alert. For 24h, predict:
- (a) the **number of alerts**;
- (b) the **total alert hours** in the next 24h;
- (c) P(any alert), kept only where it's informative.

Possible extra: P(a "night attack" alert between 22:00 and 06:00).

## D18. @air_alert_ua — finding (2026-10-11)
The channel's **last post is #338380 at 2026-09-07 06:09 UTC**, the same point where the official dataset stops. The channel stopped publishing, so it **cannot fill the gap** after 2026-09-07. Its history duplicates the official dataset, except for message types the parser may mishandle:
- 🟠 "Загроза ударних БпЛА" (strike-drone threat), sometimes "невизначеного типу" (unknown drone type);
- artillery threats ("Загроза артобстрілу");
- "УВАГА" (attention) notices.

Threat type is not reported systematically, which confirms the user's note. A full scrape (~17k pages, ~5h) is not done; it waits for a decision.

## D19. Gap filler: JustJimer/ukraine-air-alert-stats archive (alerts.in.ua) — Accepted (2026-10-11)
**Source:** https://github.com/JustJimer/ukraine-air-alert-stats, file `archive/alerts_in_ua.csv`. A GitHub Action pulls the alerts.in.ua API ("last month" for every region) daily and upserts records by API id. We can read it **without our own API key**.
**Facts (checked 2026-10-11, archive HEAD 2026-10-11 10:07 UTC):**
- 19,016 records. **Complete from about 2026-09-06 12:00 UTC → today.** Earlier rows are only a few long-running alerts (permanent Luhansk/Crimea sirens, etc.).
- Levels: raion 16,252, hromada 1,265, city 1,256 (7 big cities, e.g. Kharkiv, Dnipro, Zaporizhzhia), oblast-type 243 (incl. Kyiv City). That's 118 raions across 23 oblasts.
- **`alert_level` yellow/red is present.** It starts on 2026-09-06, matching the reform (CMU resolution 1092, per the repo README). Counts: yellow 11,284, red 7,732. `threats` is empty.
- **`alert_type` separates `air_raid` (18,686) from `artillery_shelling` (329) and `urban_fights` (1).**
- **Agreement with the official data on the overlap** (2026-09-06 12:00 → 09-07 06:10): 97% of official raion alerts match an API alert (same raion, start within 3 min); the median end-time difference is 0.5 min. So the definitions are compatible.

**Why the official feed stopped (per the repo README):** on 2026-09-06 the yellow/red split changed @air_alert_ua's message format, and the Vadimkin parser broke (upstream issues #6, #7).
**Proposal:** official (≤ 2026-09-06 12:00) + archive (from then on) = one raion-level series up to today. Volunteer only fills residual holes.
**Caveats:**
- The archive is a third-party repo with no LICENSE file. Credit it, and pin the commit we use.
- Records get upserted (end times filled in later). That's fine for historical labels. For features we still use only what was known at t.
- 6 of 150 six-hour bins have zero alerts nationwide; check whether these are real calm periods or sync holes.

### D19 follow-up: hole check (2026-10-11)
- **Volunteer alerts after 2026-09-06 12:00 vs the archive:** 95.1% are "explained" by the archive (an API alert in the same oblast starts within ±10 min or is already active).
- **The 253 unexplained alerts are concentrated in Lviv (117) and Volyn (79), then Kherson (30) and Kyiv City (15).**
  - Lviv has only 50 API raion alerts in that period. Either the volunteer source records west-Ukraine alerts the API doesn't (e.g. nationwide ballistic/MiG threats), or the API misses some.
  - This is **unresolved**: check against the @air_alert_ua messages once they're scraped.
- **Real hole: 2026-10-07 about 00:12–04:02 UTC.** The archive has **no** new alerts, while the volunteer data shows about 10 oblast alerts (Kyiv, Kharkiv, Dnipro, Mykolaiv, …) 03:05–04:00 UTC. The sources agree again from 04:02.
  - Plan: fill such holes from the volunteer data (oblast-level alert → all raions of the oblast), with a `source=volunteer` flag.
- The "6 empty 6-hour bins" mentioned earlier were before 2026-09-06 12:00, when the archive wasn't yet complete. Not a problem.

## D20. Artillery warnings inside the official dataset — finding (2026-10-11); handling decided in D25
**Method:** the Vadimkin parser sets `started_at` = the Telegram message time. Each official row is matched to the @air_alert_ua message that created it, by exact timestamp. Coverage: rows inside the windows scraped so far (5,165 rows); 93% matched.
**Findings:**
- **512 of 5,165 rows (≈10%) are artillery warnings ("🔴 Загроза артобстрілу!"), not air raids.** The parser treats every 🔴 message as an alert.
- **All of them are at hromada level: 512 of 678 hromada rows (76%).** Raion and oblast rows contain no artillery.
- They are concentrated in frontline communities: Nikopol 190, Pokrovska 127, Chervonohryhorivka 84, Marhanets 83. Median duration is 79 min.
- A few hromada rows are drone threats ("Загроза ударних БпЛА", 7) or urban fights (1).
- The archive (alerts.in.ua) labels these separately (`alert_type` = artillery_shelling / urban_fights), so it needs no cleaning.

**Proposal:** when the full scrape is done, label every official row by its message type and keep only air raids. Until then, use the rule "drop hromada-level rows". It removes all artillery but also about 18% of hromada rows that are real air raids. These are tiny areas, so the impact is small.

## D16 results: spatial options compared (2026-10-11)
Script: `scripts/explore_spatial_options.py`. Full tables: `reports/spatial_options.md`.
- Setup: official data with hromada rows dropped and old oblast-wide alerts copied to every raion. 121 raions, 24 oblasts (incl. Kyiv City). The same LightGBM, the same 13 features and the same periods for every option.
  - Train 2025-06-01 → 2026-08-09; evaluate 2026-08-10 → 2026-09-06 (before the reform; the real test period stays untouched).
- **Raion-level truth** (new alert starts in the raion):

  | | 1h AUC | 1h Brier skill | 3h AUC | 3h Brier skill |
  |---|---|---|---|---|
  | O1 oblast model | 0.770 | −0.001 | 0.808 | 0.168 |
  | **O3 raion model** | **0.839** | **0.141** | **0.849** | **0.282** |
  | O4 hierarchical (oblast × share) | 0.738 | 0.032 | 0.806 | 0.180 |

- **Oblast-level truth:** the oblast model is best (1h AUC 0.855, skill 0.17; 3h AUC 0.864, skill 0.32). Combining raion probabilities as if they were independent, 1 − ∏(1 − p), badly over-predicts (skill −0.70 at 1h): raions in one oblast are strongly correlated.
- **Conclusion (Proposed):** use the raion model (O3) for the district map, plus a separate oblast model for the oblast view. Do NOT build oblast probabilities from raion probabilities.
- Caveats: a single 4-week window, untuned models, pre-reform period.

## D21. Yellow/red — first numbers for the brainstorm (archive, 2026-09-06 → 10-11, raion + Kyiv City alerts)
- 37% of alerts are red. Red is a bit more common at night (00–06 Kyiv: 43%; other blocks 33–36%).
- It varies hugely by oblast: west 6–8% red (Rivne, Ternopil, Volyn, Khmelnytskyi); frontline 60–84% (Zaporizhzhia, Donetsk, Dnipropetrovsk).
- **Persistence:** P(red | the previous alert in the same raion was red) = 0.61; P(red | previous was yellow) = 0.22. So the level is fairly predictable from recent history.
- Median duration: yellow 42 min, red 56 min.
- 188 of 16,470 alerts switch level with no gap in between (escalation or de-escalation).
- The daily share of red ranges from 0.20 to 1.00 (std 0.15). Some days are all-red (massive missile attacks?).

---
# Decisions accepted on 2026-10-11 (evening)

## D22. Two models: raion (district) map + oblast view — Accepted
- **Raion model** (option O3): target = a new alert starts in the raion. History before the raion era is built by **disaggregation**: an oblast-wide alert = an alert in every raion of that oblast. Powers the district map.
- **Oblast model** (option O1): target = a new "any alert in the oblast" period starts. Powers the oblast view.
- Both models use **the same kinds of inputs** (recent alerts of the unit, its oblast, the whole country, time of day, …), each computed for its own unit. They differ in **what they predict**.
- Oblast probabilities are **not** computed from raion probabilities: raions are strongly correlated, so 1 − ∏(1 − p) over-predicts (D16 results).

## D23. Targets — Accepted
- **1h and 3h:** P(new alert starts within (t, t+h]) **and the expected duration** of that alert.
- **24h:** number of alerts, total hours under alert, and **when** they are most likely (a probability per hour or time-of-day block).
- The probability of a night alert is an **input feature**, not a separate output.

## D24. Yellow/red — Accepted (adapt as we go)
- Predict "**if an alert happens, how likely is it to be red?**", from recent levels (raion, oblast), time of day, and later @war_monitor missile/bomber signals.
- Train and evaluate only on the reform period (from 2026-09-06). Communicate that the data is thin (about 5 weeks).
- The map shows "chance of an alert" and "chance it's red" side by side.

## D25. Artillery warnings — Accepted
- **Do not** drop hromada-level rows wholesale.
- Wait for the full @air_alert_ua scrape. Label every official row by the message that created it (exact timestamp match), and **keep only air raids**. Drop artillery threats, urban fights and other non-air-raid messages.

## D26. Filling holes with volunteer data — Accepted, with verification
- Before using a volunteer alert to fill a hole in the archive (e.g. 2026-10-07 ~00:12–04:02 UTC), **verify it** against @air_alert_ua (before 2026-09-07) and @war_monitor posts (threat activity in that oblast around that time).
- Investigate why Lviv and Volyn have many volunteer alerts the archive lacks, and report the findings to the user.

---
# Overnight decisions (2026-10-11/12) — all Proposed, for the user's review

## D27. What counts as an alert in a raion — Proposed
- A raion is "under alert" when there is an air-raid alert for the raion itself, for its whole oblast (disaggregation, D22), or for a hromada or city inside it (e.g. "м. Харків" → Kharkivskyi raion). In words: "an alert somewhere in the raion".
- Official rows whose message could not be found (`unknown`): kept at oblast/raion level, where artillery and threat messages never occur, and dropped at hromada level, where most messages are artillery threats. Counts are in `reports/data_quality.md`.
- Name fixes: three raions renamed in 2024 (Володимирський, Шептицький, Берестинський) are mapped to the official old names, and the 7 archive cities to their raions (`src/alerts/sources.py`).

## D28. Message types excluded from targets — Proposed
The labelling (D25) found these types besides air raids in @air_alert_ua:
- artillery threats;
- urban fights;
- typed threats: strike drones "Загроза ударних БпЛА", missiles "Ракетна загроза", ballistic "Загроза балістики", guided bombs (KAB) "Загроза керованих авіабомб";
- radiation danger.

Only `air_raid` rows define targets. The typed threats are **kept as possible features** (they carry the threat type), mainly for Zaporizhzhia city.

## D29. Archive holes — Accepted (user, 2026-10-12); refined same day: also require < 50% of raions already under alert
- A hole is an archive silence of ≥ 2 h nationwide while @war_monitor posts ≥ 10 threat messages.
- Example: 2026-10-07 00:12–04:02 UTC, during a massive Kh-101 cruise-missile attack (48 threat posts).
- During a hole, raion truth is unknown, so targets overlapping the window are set to NaN (excluded from training and scoring). Oblast truth gets volunteer patches for alerts not already covered by an active archive alert (none were needed for Oct 7).

## D30. Volunteer quirk in Lviv, Volyn, Kherson — OPEN (user: find other sources before deciding)
- The volunteer source records many more alerts there than the official system:
  - Lviv: about 5/day volunteer vs about 0.5/day official before the reform;
  - after the reform: 117 of 134 Lviv volunteer alerts are not in the archive.
- @war_monitor never mentions these oblasts around the unexplained alerts.
- Conclusion: a volunteer-side quirk, not an archive gap. These alerts are never used as patches.

## D31. Time grid and splits — Proposed
- Issue times: every hour from 2024-01-01. The first training row is 2024-01-31, after a 30-day warm-up for the rate features.
- **Test period: 2026-09-13 00:00 UTC → end of data (2026-10-11 09:00).** Untouched until the user says go.
- Validation: 4 weekly walk-forward folds before the test period (Aug 16, Aug 23, Aug 30, Sep 6). Training rows are purged so their target windows end before the fold starts.
- The training-window length (all since 2024 / 12 / 6 / 3 months) is compared on the folds (D7).

## D32. Yellow/red split — Accepted (user, 2026-10-12: 3 weeks train + 2 weeks test)
- There are only about 5 weeks of data with levels, so the red model gets its own split:
  - train from 2026-09-06;
  - validate on the weeks of Sep 13–19 and Sep 20–26;
  - test on Sep 27 → end.
- This overlaps the main test window, but it's a different model, and the main models never see these weeks during validation.
- The alternative (validate only inside Sep 6–12) leaves a single week of training. That's too thin.

## D33. 24h timing target — Proposed
"When are alerts most likely?" = four probabilities: a new alert starts in hours +0–6, +6–12, +12–18 or +18–24 after the issue time. On the website these can be shown in local clock time.

## D34. Small technical choices — Proposed
- "Same hour, last N days" rates use the UTC hour (the DST shift is ignored; it's a 1-hour offset twice a year).
- LightGBM settings are fixed and not tuned yet: 400 trees, learning rate 0.05, 63 leaves, min 500 rows per leaf.
- Logistic regression gets log-transformed counts and sine/cosine of hour and weekday.

## D35. Model choice after validation — Proposed (see reports/validation.md)
- New-alert probabilities (1h, 3h; raion and oblast) and 24h timing: **LightGBM**, trained on the last 12 months.
- 24h count and hours, and duration: LightGBM is only marginally better than persistence. Show them as **typical ranges** (e.g. "usually 30–120 min"), not precise numbers. Candidates for improvement: quantile models, features from Telegram.
- Red given alert: the **simple rule "raion red share in the last 7 days"** or the 5-feature logistic regression. Full models overfit the ~2–3 weeks of reform data.

---
# User feedback 2026-10-12 (morning)

## D36. Role of each source — Accepted (user principle)
- **Whether** there is an alert, and its details: official data (until 2026-09-07) and alerts.in.ua (JustJimer archive).
- **What kind** of threat it is: @war_monitor. It is not reliable for tracking alerts themselves.
- The hole rule (D29) follows this: the archive decides; @war_monitor only flags "a big attack was going on, so silence is suspicious".

## D37. 🟠 "Загроза ударних БпЛА / Загроза БпЛА невизначеного типу" = FPV-type drones — Accepted (user's interpretation)
These posts only appear for frontline communities (Nikopol 8,495, Kharkiv 3,172, Zaporizhzhia 933). They are a separate, local threat type, not the yellow "drone" alert level.

## D38. @war_monitor as a yellow/red labeller — tested, does NOT work well enough (2026-10-12)
**Test:** for 11,162 alert groups since 2026-09-06 (oblast × start minute, true level known; 29% red), rules based on @war_monitor posts within −60…+15 min of the alert start:

| Rule | Balanced accuracy | Red precision | Red recall |
|---|---|---|---|
| any nationwide missile post → red | 0.56 | 0.44 | 0.24 |
| missile post naming the oblast → red | 0.51 | 0.60 | 0.03 |
| oblast missile, or nationwide missile and no oblast drone | 0.56 | 0.46 | 0.22 |
| score (oblast missile, nationwide missile, oblast drone) | AUC 0.57 | | |

Balanced accuracy 0.5 = coin flip. Other windows (−30…+10, −120…+30) give the same picture.

**Why:**
- @war_monitor names the oblast in only 12% of alerts: Kyiv City 47%, Kyiv oblast 41%, but 0–3% for frontline oblasts where red is common (Dnipropetrovsk 86% red, Donetsk 70%, Kharkiv 56%).
- Red there is mostly local aviation/KAB/missile activity the channel doesn't cover.

**Consequence:** we don't create pseudo yellow/red labels for August and earlier from @war_monitor. Its posts remain candidate *features* (e.g. "missile activity nationwide in the last hours").

## D39. Artillery warnings — OPEN (to discuss with the user)
Facts:
- 22,273 official rows in 18 hromadas since 2022-05.
- Since 2026, effectively only **Nikopol** (under an artillery warning ~68% of the time), **Marhanets** (~100%; warnings overlap) and **Pokrovska** (until 2026-07) and **Chervonohryhorivka** (until 2026-03).
- After the reform the archive has artillery warnings only for Nikopol and Marhanets (322 records).

Options:
- (a) Keep them out of the air-raid targets (current).
- (b) Add them as a separate small target "artillery warning starts in hromada X", for the 2 active communities.
- (c) Count them as alerts for their raion.

---
# Accepted 2026-10-12 (afternoon)

## D40. History used for training — Accepted (user), from reports/training_window.md
- **Oblast models:** full history (from 2022-04) with **recency weights**, half-life 12 months: a row from d days before the training cut-off gets weight 0.5^(d / 365).
- **Raion models:** the **last 12 months** only. Older raion rows are copies of oblast-wide alerts (disaggregation) and teach a pattern that no longer exists.

## D41. Presentation of the weak targets — Accepted (user)
- Duration: a range "usually X–Y min" = predicted 25th–75th percentile (LightGBM quantile models).
- Duration bands are not shown.
- 24h count and hours under alert: shown as ranges.

## D42. Timing model (plan C) — Accepted (user)
One LightGBM predicts P(new alert starts) for each 3-hour **Kyiv-time** block of the next 7 days (56 blocks). Blocks 1–8 = "next 24h: approximately when"; all 56 = the week-ahead heatmap and a week-ahead strip.

## D43. Website — Accepted (user)
- Title: **"Time-Series Air Alert Forecast, Ukraine (demo)"**.
- **Desktop only** (no phone layout).
- **Leaflet 1.9.4 from cdnjs** approved as the map library. No external map tiles.
- All times shown in **Kyiv time**.
- Click panel: history strip (actual alerts + predicted probability on the same timeline) **and a separate week-ahead strip**.
- Pages: Map, Replay (test weeks), How good is it? (incl. with vs without Telegram), About.

## D44. Telegram (@war_monitor) as input — result: NOT used (rule agreed with the user)
`reports/telegram_ablation.md`, 4 validation weeks, accepted training history (D40):

| Target | Raion without / with | Oblast without / with |
|---|---|---|
| 1h skill | 0.186 / 0.179 | 0.214 / 0.208 |
| 3h skill | 0.326 / 0.279 | 0.366 / 0.353 |
| 24h count MAE | 1.48 / 1.50 | 1.64 / 1.67 |
| 24h hours MAE | 1.91 / 1.95 | 2.02 / 2.06 |

@war_monitor makes every target slightly worse, so the map uses the plain models. Both are shown on "How good is it?".

**@kpszsu tested (2026-10-12, `reports/kpszsu_ablation.md`, same protocol): NOT used.**

| Target | Raion without / with | Oblast without / with |
|---|---|---|
| 1h skill | 0.186 / 0.187 | 0.214 / 0.190 |
| 3h skill | 0.326 / 0.296 | 0.366 / 0.332 |
| 24h count MAE | 1.48 / 1.49 | 1.64 / 1.62 |
| 24h hours MAE | 1.91 / 1.93 | 2.02 / 2.03 |

Only the oblast 24h count improves slightly; every probability target is the same or worse. Caveat: @kpszsu exists only since 2025-08-31, so the oblast model (full history) sees it as "unknown" for most of its training rows.

## D45. Timing model: blend of model and pattern rule — Accepted (user, 2026-10-12)
`reports/timing_validation.md` (first look) and `reports/timing_variants.md` (7 variants), 2 validation weeks.
- Model vs pattern by lead day (AUC): day 1 0.803 vs 0.759 (raion), 0.804 vs 0.769 (oblast); day 2 +0.02/+0.01; days 3–7 about equal, and the model's Brier is worse there.
- Variants tried: pattern, full model, calendar-only model (no "alerts now" inputs; the user's idea), hybrid A (model < 48 h, then pattern), hybrid B (model < 48 h, then calendar-only), blend model/calendar-only, blend model/pattern.
- The calendar-only model did NOT help (raion Brier 0.2085 vs 0.1787 for the pattern): without the current-state inputs it ranks no better than the pattern and is worse calibrated. Any variant using it as the far end was worse than the pattern.
- **Decision:** week-ahead probability = `w × model + (1 − w) × pattern rule`, `w = clip(1 − lead_h / 72, 0, 1)` (fixed schedule, nothing fitted). Overall Brier skill vs pattern: raion +0.016, oblast +0.024; hybrid A was +0.014 / +0.023 (practically a tie, but the blend has no jump at 48 h).
- Code: `src/alerts/timing.py` (`blend_weight`, `blend_timing`), tests in `tests/test_timing_blend.py`.
- Caveat: only 2 validation weeks; the blend vs hybrid A difference (≤ 0.0003 Brier) is within noise.

## D46. @UkraineAlarmSignal — candidate second alert source (2026-10-12)
- An alert feed: raion/city, **yellow/red level**, all-clears, local typed threats (БПЛА, КАБ).
- About 1,500 posts/day, 93% name an oblast. History since 2022-02-25 (~654k posts).
- Being downloaded for the reform period only (since 2026-09-01).
- Uses:
  - an independent cross-check of the JustJimer archive (holes, Lviv/Volyn, D30);
  - yellow/red truth;
  - per-city threat-type inputs.

## D15 (follow-up). Commit compressed Telegram data — Accepted (user, 2026-10-12)
Re-scraping takes hours (@air_alert_ua alone ~5 h). Proposal: commit `.jsonl.gz` copies of the scraped channels and `official_labels.parquet` (tens of MB) so a new session/container doesn't need to re-download.
Done: `data/telegram/*.jsonl.gz` (all scraped channels, 8.3 MB; @kpszsu and @UkraineAlarmSignal are PARTIAL snapshots taken mid-download) and `data/labels/official_labels.parquet` (5 MB). Restore with `scripts/restore_data.sh`.

## D47. LightGBM settings for the new-alert classifiers (1h, 3h) — Accepted (user, 2026-10-12)
`reports/tuning.md`, `scripts/tune_lgbm.py`. 12 candidates (current + 11 drawn from a grid fixed in advance), 4 validation weeks, test untouched. Adoption rule fixed before running: better than the current settings in ≥ 3 of 4 weeks, ≥ 0.5% lower average Brier, not worse on 1h.

| Level | Chosen settings | 3h Brier current → new | weeks better | 3h skill | 1h Brier current → new |
|---|---|---|---|---|---|
| Raion | 31 leaves, min 500 rows/leaf, lr 0.03 × 700 trees, 60% of inputs per tree | 0.1333 → 0.1320 (−1.0%) | 4 of 4 | 0.326 → 0.333 | 0.0771 → 0.0769 |
| Oblast | 31 leaves, min 1000 rows/leaf, lr 0.03 × 700 trees, 60% of inputs per tree | 0.1269 → 0.1258 (−0.8%) | 3 of 4 | 0.366 → 0.371 | 0.0799 → 0.0794 |

- Pattern: simpler trees and fewer inputs per tree help a little; the most complex trees (127 leaves) are the only clearly worse option. The current settings were slightly too detailed.
- Gains are small (about +0.005–0.007 skill) but consistent.
- Scope: only the 1h/3h new-alert classifiers. Duration, 24h count/hours, timing and red/yellow keep the D34 settings.
- Alternative: one setting for both levels (candidate 4 also passed for oblast, −0.5%); the rule picks the lowest Brier, so candidate 6 for oblast.

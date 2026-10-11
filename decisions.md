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

## D3. Spatial unit = oblast (25 units incl. Kyiv City) — Proposed
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

## D13. District (raion) level forecasts — Proposed (brainstorm later)
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

## D16. Spatial unit: oblast vs raion — OPEN (options to evaluate)
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

## D17. 24h horizon reframing — Proposed (user idea)
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

## D20. Artillery warnings inside the official dataset — finding (2026-10-11)
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

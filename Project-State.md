# Project State

_Last updated: 2026-10-13, ~15:00 Kyiv (session 4: D58/D59 data fixes, D55 neighbours, retrained, final site version **shipped**).
Merged as PR #17 (`[skip netlify]`); one manual live run (#7, 11:30–11:47 UTC) published the forecast of 13 Oct 14:00 Kyiv from
the latest API data = the one Netlify update. Hourly runs stay paused (frozen forecast, user's choice). This file's last edit is
on the work branch only, to avoid another Netlify update._ The deadline version (2026-10-12 23:59 Kyiv) is **done and live**.

## Session 5 (2026-10-15): Forecast check update (D60), on the work branch, awaiting the user's approval
- The live Forecast check showed only the two pre-fix forecasts (Kharkivskyi 0% everywhere). Added: the corrected models'
  published forecast of 13 Oct 14:00 (archived from git `de0fcbf`), re-runs of 11 and 12 Oct 12:00 (`predict_now.py --asof`,
  trained only on data before each moment; `site/data/archive/rerun/`), scoring of partial first blocks (only hours after the
  forecast), paired published/re-run cards with a comparison table. Data to 15 Oct 12:00 Kyiv (JustJimer `b77413ed`).
- District AUC, published → re-run: 11 Oct 0.791 → 0.812, 12 Oct 0.805 → 0.817; oblast 0.808 → 0.836, 0.793 → 0.800.
  13 Oct published (corrected models): 0.779 districts, 0.747 oblasts. Kharkivskyi: re-runs 66–88% per block, counts in range.
- Tests: 23. Not published: needs the user's approval (one Netlify update).

## Session 4 (2026-10-13), on the work branch only
- **D58 (Accepted): local alerts are not district alerts.** Hromada/city alerts used to count for their whole district; Lyptsi
  hromada (one alert 2024-05-12 → 2026-01-06, again since 2026-03-10) made Kharkivskyi district and Kharkiv oblast look
  permanently under alert ("continuous alert 7+ days", ~0% forecast). Now: district table = district/oblast-wide alerts only;
  `data/processed/alerts_local.parquet` keeps the local ones (site notes). Time under alert 1 Aug–11 Oct: Kharkivskyi 100% → 68%,
  Nikopolskyi 75% → 32%, Oleksandriiskyi 37% → 23%; 28 of 119 districts change by > 1 point.
- **D59 (Accepted): data errors found by the new guards.** Official-feed outage 2026-08-29 04:55 → 09-02 13:48 (105 h) masked and
  patched from volunteer data (it made 10 oblasts look under alert for ~4.8 days, inside the validation weeks); stuck alerts in
  Mukachivskyi/Berehivskyi (Nov 2025, 122 h) fixed via the reviewed list `data/fixes/stuck_alerts.csv`. Guards in
  `reports/data_quality.md` (sections 2c, 4b).
- **D55 (Accepted, done): neighbour inputs kept.** `data/neighbours.json` (from full-detail boundaries, `scripts/build_neighbours.py`).
  Validation weeks (`reports/local_neighbours_ablation.md`), skill vs same-hour rule, base → + neighbours: district 1 h 0.133 →
  0.140, 3 h 0.334 → 0.339; oblast 1 h 0.176 → 0.185, 3 h 0.372 → 0.378. Local-alert inputs did not win → not used.
- **Models retrained** (data to 2026-10-13 09:00 UTC; Vadimkin `1e5d1b46`, JustJimer `f7b33ebc`, `data/versions_live.json`) with the
  neighbour inputs; `models/meta.json` records the inputs. Local run of the hourly steps: Kharkivskyi 3 h = 73% (was 0.1%).
- Site: local-alert notes (EN transliterated, `src/alerts/translit.py`), corrected continuous-alert text, the test pages labelled as
  the deadline version. Generated `site/data/` is **not** committed (the hourly run writes it on `main`).
- **No fair test yet** for the corrected version: the old test weeks are used up; needs 2–4 new weeks (from ~27 Oct / ~10 Nov).
- Tests: 21 (new: `tests/test_alert_tables.py`; local/neighbour leakage tests, checked to fail on a planted leak).
- **Final site version** (user, 2026-10-13: "the next Netlify version will be our final"): banner "Hourly updates are paused …" when
  the forecast is > 2 h old (panel heading "At the forecast time"); "How good is it?" section 9 (13 Oct update + validation chart);
  Forecast check notes which models made each forecast (old snapshots = deadline models, scored on corrected data); About and
  Replay updated (neighbours, corrections, paused updates). Hourly runs stay **paused** (user: one frozen forecast from the latest
  API data). Shipping = merge with `[skip netlify]` + one manual live run (= one Netlify update).

## Live site
**https://air-alert-forecast-ua.netlify.app**: Netlify publishes `site/` from `main`.
- Pages: Map, Replay, Forecast check, How good is it?, About; **EN | UA** switch (`?lang=uk`).
- Design: **Editorial Dark** (default). Other looks via `?theme=classic|glass|light|civic`.
- Map panel: "Right now · updated every hour" (big 3-hour number, 1 h / duration / red tiles, 24 h count and hours) and
  "Outlook" (next 8 three-hour blocks, week heatmap, week strip), then the 7-day history strip.
  "Major cities" card (Kyiv, Lviv, Kharkiv, Odesa; 1 h and 3 h).
- Site QA fixes (session 3, website only, D56; QA list in `tasks.md`):
  - districts/oblasts **under alert now** are striped red ("under alert since HH:MM"); an alert running **24 h+** is a
    "continuous alert" with no forecast (12 Oct: Kharkivskyi and Nikopolskyi districts, Kharkivska and Dnipropetrovska oblasts);
  - the outlook blocks (made at 00:00 / 12:00) are labelled as older than the hourly numbers; the block already in progress is
    left out and blocks overlapping the next 3 h are dashed;
  - history strip: hours without a saved forecast are a grey gap (found via `p3_log.json`), not 0%;
  - red tile shows its evidence ("0 of 15 alerts here in 7 days were red; nationally 26%"), never a bare 0% / 100%;
  - About (EN + UA) describes the live hourly system; model training date read from `meta.json`.
  - All of it is computed in the browser from `history.json` / `p3_log.json`; the pipeline and the forecasts are unchanged.

## Live system (D51, D52)
- **PAUSED 2026-10-13 ~09:00 UTC** (user): Netlify credits at 75% of 300 (each `site/data` commit = one production
  deploy). Hourly schedule and chain switched off in `live.yml`; site shows the last forecast. Fix planned: data not via deploys.
- **Hourly** (`.github/workflows/live.yml`, ~15 min; started by cron at :07/:27/:47 UTC plus a self-dispatch chain at :05,
  D57, because GitHub skipped most cron slots on 12–13 Oct; a run whose hour is already on `main` skips itself): alerts.in.ua API (`scripts/fetch_live.py`, token in the
  GitHub secret `ALERTS_IN_UA_TOKEN`) → `build_alert_table.py` → `build_panel.py` (last 50 days) →
  `predict_now.py --predict` (saved models, latest hour) → `export_site.py` → `forecast_check.py` → commits **only
  `site/data/`** to `main` (approved exception) → Netlify redeploys. A failed run commits nothing and shows red.
- **Retrain** (`.github/workflows/retrain.yml`, 1st and 15th of each month, or by hand): `predict_now.py --train` →
  pull request with `models/` for the user to merge.
- Models in `models/` (12.5 MB gzipped LightGBM text + `meta.json`), trained on data to **2026-10-12 12:00 Kyiv**.
- Week view issued at 00:00 / 12:00 Kyiv; history strip from a rolling log of the site's own forecasts
  (`site/data/p3_log.json`); Forecast check archives the 00:00 / 12:00 forecasts (`site/data/archive/`).
- Run #1 (19:20 UTC) fetched fine but did not publish (fixed in PR #10); **run #2 (19:51 UTC) published**.
- **No scheduled (cron) run had started by 20:35 UTC** (the 20:07 slot was skipped); only the two manual runs exist. GitHub
  often delays new schedules, but this needs watching. Until the next run, `now.json` has no `active` flag (the site derives
  it from `history.json`).

## Method in short (details: `docs/how_it_works.md`, `decisions.md`)
- Data: official dataset to 2026-09-06 (non-air-raid rows removed via @air_alert_ua labels) + alerts.in.ua archive
  (JustJimer; from 2026-09-06 with yellow/red) + live API. 119 raions, 24 oblasts (Luhansk, Crimea excluded).
- Hourly tables per raion / oblast since 2022-03; every input uses only data before the forecast time (21 tests).
- Models: LightGBM (tuned, D47) for 1 h / 3 h; LightGBM quantile models for duration and 24 h ranges (D41, D49);
  week view = blend of timing model and pattern rule (D45); red vs yellow = the raion's red share over 7 days (D35).
  Raion: last 12 months; oblast: full history with recency weights (D40). Telegram not used (D44).

## Final test (13 Sep – 11 Oct 2026, scored once; `reports/test_results.md`)
| | District | Oblast |
|---|---|---|
| New alert 1 h: AUC / skill | 0.822 / 0.148 | 0.825 / 0.164 |
| New alert 3 h: AUC / skill | 0.836 / 0.339 | 0.854 / 0.402 |
| Duration range coverage (ideal 50%) | 48% | 49% |
| 24 h hours: vs 7-day average | 8% better | 8% better |
| 24 h count: vs 7-day average | **4% worse** | **8% worse** |
| Week blend: skill vs pattern | +0.003 | **−0.035** |
| Red vs yellow AUC (test from 27 Sep) | 0.845 | — |

Weak spots kept and reported (D48). Forecast check of the 11 Oct 12:00 forecast: AUC 0.81 (districts) / 0.86 (oblasts).

## Data versions
- Test scores: `data/versions.json` (Vadimkin `bf0c323c`, JustJimer `7abc556b`); test period fixed in code
  (`TEST_START` / `TEST_END` in `scripts/validate_models.py`).
- Models: trained on Vadimkin `d10c80fa`, JustJimer `c5b3bd01` (`data/versions_live.json`, `models/meta.json`).
- Telegram snapshots in git (`data/telegram/*.jsonl.gz`, complete): @war_monitor 46,492 posts (2022-04 → 2026-10-11;
  no posts after 11 Oct 10:02), @air_alert_ua 338,360 (→ 2026-09-07), @kpszsu 44,057 (2025-08-31 → 2026-10-12),
  @UkraineAlarmSignal 45,875 (2026-08-31 → 2026-10-12).

## In a fresh container
```
python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
bash scripts/restore_data.sh
python scripts/download_data.py --pin            # or without --pin for the newest data
PYTHONPATH=. python scripts/build_alert_table.py
PYTHONPATH=. python scripts/build_panel.py --start 2022-03-01
PYTHONPATH=. python -m pytest -q tests/          # 21 tests
```
Full command list: `README.md`. Run heavy model jobs one at a time.

## Next (planned, not started): `docs/next_steps.md`
1. Task 5: keep the repo small (live data on a `live-data` branch + Netlify build hook; models as GitHub Releases), D54.
2. Task 3: faster hourly runs (rolling API refresh, ~5 min per run), D53; after task 5.
3. ~~Task 4: neighbouring-district inputs (D55)~~ done 2026-10-13 (with D58/D59); fair test on new weeks still to do.

Not started, from the site QA (`tasks.md`): pipeline versions of the panel fix (stitch the hourly forecast into the near
blocks) and of the red share (shrinkage toward the national share); staleness banner; "next 1 h" window partly over when
published; Forecast check partial-day labels; layout polish.

## Open items for the user
- Review the Ukrainian texts on the site (including the new About paragraphs and panel texts).
- Watch the scheduled hourly runs (GitHub → Actions → live-forecast): none had started by 20:35 UTC.

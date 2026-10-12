# Project State

_Last updated: 2026-10-12, ~23:00 Kyiv (end of session 2)._ The deadline version (2026-10-12 23:59 Kyiv) is **done and live**.

## Live site
**https://air-alert-forecast-ua.netlify.app**: Netlify publishes `site/` from `main`.
- Pages: Map, Replay, Forecast check, How good is it?, About; **EN | UA** switch (`?lang=uk`).
- Design: **Editorial Dark** (default). Other looks via `?theme=classic|glass|light|civic`.
- Map panel: big 3-hour number, 1 h / duration / red tiles, next 24 h blocks, week heatmap, 7-day history strip.
  "Major cities" card (Kyiv, Lviv, Kharkiv, Odesa; 1 h and 3 h) and "under alert now" flags.

## Live system (D51, D52)
- **Hourly** (`.github/workflows/live.yml`, :07 UTC, ~15 min): alerts.in.ua API (`scripts/fetch_live.py`, token in the
  GitHub secret `ALERTS_IN_UA_TOKEN`) → `build_alert_table.py` → `build_panel.py` (last 50 days) →
  `predict_now.py --predict` (saved models, latest hour) → `export_site.py` → `forecast_check.py` → commits **only
  `site/data/`** to `main` (approved exception) → Netlify redeploys. A failed run commits nothing and shows red.
- **Retrain** (`.github/workflows/retrain.yml`, 1st and 15th of each month, or by hand): `predict_now.py --train` →
  pull request with `models/` for the user to merge.
- Models in `models/` (12.5 MB gzipped LightGBM text + `meta.json`), trained on data to **2026-10-12 12:00 Kyiv**.
- Week view issued at 00:00 / 12:00 Kyiv; history strip from a rolling log of the site's own forecasts
  (`site/data/p3_log.json`); Forecast check archives the 00:00 / 12:00 forecasts (`site/data/archive/`).
- Run #1 (19:20 UTC) fetched fine but did not publish (fixed in PR #10); **run #2 (19:51 UTC) published**. Hourly since then.

## Method in short (details: `docs/how_it_works.md`, `decisions.md`)
- Data: official dataset to 2026-09-06 (non-air-raid rows removed via @air_alert_ua labels) + alerts.in.ua archive
  (JustJimer; from 2026-09-06 with yellow/red) + live API. 119 raions, 24 oblasts (Luhansk, Crimea excluded).
- Hourly tables per raion / oblast since 2022-03; every input uses only data before the forecast time (13 tests).
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
PYTHONPATH=. python -m pytest -q tests/          # 13 tests
```
Full command list: `README.md`. Run heavy model jobs one at a time.

## Next (planned, not started): `docs/next_steps.md`
1. Task 5: keep the repo small (live data on a `live-data` branch + Netlify build hook; models as GitHub Releases), D54.
2. Task 3: faster hourly runs (rolling API refresh, ~5 min per run), D53; after task 5.
3. Task 4: neighbouring-district inputs (~5 h of work + 2–4 weeks for a fair test), D55.

## Open items for the user
- Review the Ukrainian texts on the site.
- Watch the first scheduled hourly runs (GitHub → Actions → live-forecast).

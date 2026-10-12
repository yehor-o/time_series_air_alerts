# Time-Series Air Alert Forecast, Ukraine (demo)

Forecasts of **air raid alerts in every Ukrainian district (raion) and oblast**: the chance that a new alert starts in the
next 1 and 3 hours, how long it would last, how many alerts and hours under alert to expect in the next 24 hours,
when in the coming week alerts are most likely (3-hour Kyiv-time blocks), and whether an alert is likely to be red
(missiles) or yellow (drones). Results are shown on a static website with a map of Ukraine.

**Live site:** <https://air-alert-forecast-ua.netlify.app> (desktop browser recommended)

> **Disclaimer.** This is a student demo, not an official warning system. Do not use it for safety decisions.
> Always follow official air raid alerts.

## Results (test period 13 Sep – 11 Oct 2026, scored once)

All choices were made on earlier validation weeks and frozen before the test; nothing was changed afterwards
(`decisions.md`, D48). Full tables: [`reports/test_results.md`](reports/test_results.md).

| What we predict | District | Oblast | Simple rule for comparison |
|---|---|---|---|
| New alert within 1 h: AUC / skill | 0.822 / 0.148 | 0.825 / 0.164 | clock-hour rule: AUC 0.733 / 0.740 |
| New alert within 3 h: AUC / skill | 0.836 / 0.339 | 0.854 / 0.402 | clock-hour rule: AUC 0.759 / 0.784 |
| Duration range contains the true duration | 48% | 49% | ideal 50%; last-10-alerts rule 42–43% |
| Hours under alert, next 24 h: average miss | 1.87 h | 2.06 h | 7-day average: 2.03 / 2.23 h |
| Number of alerts, next 24 h: average miss | 1.72 | 2.09 | 7-day average: 1.66 / 1.93 (**ours is worse**) |
| Week-ahead blocks: skill vs pattern rule | +0.003 | −0.035 (**worse**) | pattern rule |
| Red vs yellow: AUC | 0.845 | — | previous alert's level: 0.712 |

*AUC*: the chance that an hour with a new alert gets a higher forecast than an hour without one (0.5 = guessing).
*Skill*: how much smaller the forecast error (Brier score) is than the clock-hour rule (0.3 = 30% smaller).
The 1 h / 3 h probabilities are well calibrated: when the model says 45%, an alert started in about 46% of cases.

## How it works

- **Data**: one row per district per hour (about 4.8 million rows since March 2022). Each row holds what was known at
  that hour and what happened afterwards.
- **No leakage**: every input uses only data published before the forecast time; an alert still running is known only
  as "started, still active". Unit tests check this (`tests/`).
- **Models**: LightGBM (gradient-boosted decision trees) for the alert probabilities, durations, 24-hour numbers and
  timing; a simple rule (the district's red share over the last 7 days) for red vs yellow. District and oblast have
  separate models.
- **Evaluation**: splits by time only. Walk-forward validation weeks (16 Aug – 12 Sep 2026) for every choice, then one
  test run on the following four weeks.
- **Telegram** (@war_monitor, @kpszsu) was tested as an extra input and did not help, so it is not used.

Plain-English explanation of the whole method: [`docs/how_it_works.md`](docs/how_it_works.md).
Every design decision, with the alternatives considered: [`decisions.md`](decisions.md).

## Repository layout

| Path | Contents |
|---|---|
| `src/alerts/` | Data sources, feature engineering, timing blocks, Telegram parsing |
| `scripts/` | Pipeline steps: download, build tables, validation, tuning, final test, live forecast, site export |
| `tests/` | Leakage tests (features must not look into the future) |
| `reports/` | Validation and test results, hourly test predictions, screenshots |
| `site/` | The static website (HTML/CSS/JS + JSON data); published by Netlify (`netlify.toml`) |
| `data/telegram/`, `data/labels/` | Compressed snapshots of the scraped Telegram channels and message labels |
| `data/raw/`, `data/processed/` | Downloaded and built data (not committed; recreated by the steps below) |

## Reproduce

Python 3.13. Run from the repository root. Times are for 4 CPU cores.

```bash
python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

bash scripts/restore_data.sh                                   # Telegram snapshots -> data/raw/ (seconds)
python scripts/download_data.py --pin                          # alert data at the pinned commits (data/versions.json)
PYTHONPATH=. python scripts/build_alert_table.py               # alert tables + data-quality report (~5 min)
PYTHONPATH=. python scripts/build_panel.py --start 2022-03-01  # hourly tables (~5 min)
PYTHONPATH=. python -m pytest -q tests/                        # leakage tests

# optional: the validation experiments behind the decisions
PYTHONPATH=.:scripts python scripts/validate_models.py         # also compare_windows, compare_telegram, compare_kpszsu,
                                                               # validate_timing, validate_timing_variants, tune_lgbm (~40 min)

PYTHONPATH=.:scripts python scripts/final_test.py              # the final test -> reports/test_results.md (~12 min)
PYTHONPATH=.:scripts python scripts/predict_now.py             # live forecast -> reports/now_predictions.json (~9 min)
PYTHONPATH=. python scripts/export_site.py                     # -> site/data/*.json
PYTHONPATH=. python scripts/forecast_check.py                  # archive the forecast + check old ones -> site/data/check.json
cd site && python3 -m http.server 8765                         # open http://localhost:8765
```

Run the heavy model scripts one at a time.

Pinned data (`data/versions.json`): Vadimkin dataset commit `bf0c323c`, JustJimer archive commit `7abc556b`
(data up to 2026-10-11). Running `download_data.py` without `--pin` takes the newest data instead.

## Data and credits

- **Official alerts 2022-03 → 2026-09-07**: [Vadimkin/ukrainian-air-raid-sirens-dataset](https://github.com/Vadimkin/ukrainian-air-raid-sirens-dataset),
  parsed from the official @air_alert_ua Telegram channel. We removed artillery and other non-air-raid warnings by
  matching each row to its original message.
- **Alerts since 2026-09-06, with yellow/red levels**: [JustJimer/ukraine-air-alert-stats](https://github.com/JustJimer/ukraine-air-alert-stats),
  a daily archive of the [alerts.in.ua](https://alerts.in.ua) API. That repository has no licence file; it is credited here
  and its data is used unchanged.
- **Telegram channels** @air_alert_ua, @war_monitor, @kpszsu and @UkraineAlarmSignal, read via their public web previews (`t.me/s/...`).
- **District boundaries**: OCHA administrative boundaries (via the Vadimkin repository).
- **Map library**: [Leaflet](https://leafletjs.com) 1.9.4.

## Licence

No licence has been chosen yet; all rights reserved by the author.

# CLAUDE.md — Air Raid Alert Forecasting (Ukraine)

Read this file first in every session. Then read `Project-State.md`, `tasks.md` and `decisions.md`.

## Project in one paragraph

We forecast **the probability of an air raid alert in each Ukrainian oblast** for the next **1, 3 and 24 hours**. We train on the historical alert data and evaluate on the **most recent period**. We compare several models against simple baselines. Then we test whether adding Telegram data (e.g. `@war_monitor`) improves the forecasts. Results are shown on a static English website with a map of Ukraine, hosted on Netlify.

**Deadline: Monday 2026-10-12, 23:59 (Kyiv time).** Scope decisions must respect this.

## Working agreement with the user (MANDATORY)

The user owns this project and must understand and approve what happens.

1. **Ask before acting** on anything beyond the task the user just approved. Always ask before:
   - pushing to GitHub, opening PRs, or changing branches;
   - installing packages or adding dependencies;
   - downloading new data sources or scraping anything (including Telegram);
   - creating accounts or API keys, or using credentials;
   - deleting or overwriting files or data;
   - changing a decision in `decisions.md`.
2. **Report everything you did**, including commands that only read or inspect things. End each work block with a short handoff: done / not done / next / questions.
3. **Explain, don't just do.** The user is learning. When you introduce a concept (a model, a metric, a feature, leakage, calibration, etc.), explain it in plain English: what it is, why we use it, and what the numbers mean. Avoid unexplained jargon. Give analogies when helpful.
4. Never present a result you did not actually compute. If something failed or was skipped, say so.
5. **Approved websites only.** The environment has full network access, but Claude may only visit sites the user approved:
   - `github.com` / `raw.githubusercontent.com`: the Vadimkin dataset and this repo
   - `t.me`: the public web preview of `@war_monitor`
   - `pypi.org`: package installs (approved for Python libraries)

   Anything else (e.g. `alerts.in.ua`, news sites, other Telegram channels) needs approval first. Add each newly approved site to this list.

## Git workflow (agreed)

- Work always happens on a dedicated branch (for this session: `claude/quirky-maxwell-imel4t`). Commit and push there freely.
- When the user says **"merge in main"**: push, open a PR into `main`, merge it.
- Never push directly to `main` otherwise.

## THE core rule: no data leakage

A forecast is made at time **t** (the "issue time"). Everything the model uses must have been **known before t**.

- Features are computed only from events with timestamp `< t`.
- An alert that is **ongoing at t** is known only as "started at s, still active". Its end time is NOT known.
- No centered rolling windows, no backward-fill, no full-dataset statistics (means, scalers, target encodings) that include data after the training cutoff.
- Splits are **by time only**: train → validation → test, in chronological order. Never shuffle.
- Hyperparameters and model choice are decided on validation folds only. The **test period is touched once**, at the end.
- Text data (Telegram/news) is used only if its **publication timestamp** is `< t`.
- Dataset revisions: the source repo is updated daily and may fix old rows. Pin the dataset commit used for each experiment (record it in `Project-State.md`).
- Every feature function needs a unit test that checks it does not look into the future (e.g. shuffling or deleting all data after t must not change the feature value at t).

## Conventions

- Language: Python 3.13 in a virtualenv: `python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt`. Main libs: pandas, numpy, scikit-learn, LightGBM, plus requests, beautifulsoup4 and lxml for scraping, matplotlib, pyarrow and pytest. Add new libraries only with approval.
- All timestamps are stored in **UTC**. Calendar features (hour of day, weekday) are computed in **Europe/Kyiv** local time.
- Spatial unit: **oblast** (see `decisions.md`).
- Code goes in `src/`, scripts and pipeline steps in `scripts/`, exploration in `notebooks/`, website in `site/`, results (metrics, figures, prediction JSON) in `reports/`.
- Raw downloaded data goes in `data/raw/` and is not committed (see `decisions.md`). Processed data goes in `data/processed/`.
- Keep every experiment reproducible: fixed random seeds, pinned dataset commit, and the exact config saved next to its metrics.
- English for code, docs and the website.

## Keeping the context files current

- `Project-State.md`: update at the end of every work block (what exists, what works, the latest numbers).
- `tasks.md`: tick off tasks and add new ones as they appear.
- `decisions.md`: add an entry for every architectural choice, with the reasoning and the alternatives considered. Status is `Proposed` until the user accepts it.

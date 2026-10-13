# Next steps (planned, not started)

Written 2026-10-12, after the deadline version went live. Order: **task 5 before task 3** (task 3 needs the persisted
archive that task 5 introduces). Each needs the user's approval before it starts.

Measured sizes at the time of writing: site data ~0.9 MB, models 12.5 MB, git pack 12 MB.

---

## Task 5: keep the repository small (D54, Proposed) — about 1.5–2 h + ~5 min of the user's time in Netlify

**Problem.** Every hourly bot commit changes ~0.4 MB of JSON (~60 KB after git compression): ~1.5 MB/day,
~45 MB/month. Each retrain adds 12.5 MB of models: 25 MB/month. Together ~70 MB/month, ~850 MB/year. GitHub warns
above 1 GB, and every clone (including each hourly run's checkout) gets slower.

**Plan.**
1. **Live data out of `main`'s history.**
   - The hourly workflow writes `site/data/` to a separate branch `live-data` that always holds a single commit
     (replaced each hour, so no history builds up).
   - Netlify keeps building from `main`; its build command copies `site/data/` from `live-data`.
   - The workflow triggers the deploy through a Netlify **build hook** (a secret URL the user creates in Netlify, stored
     as the GitHub secret `NETLIFY_BUILD_HOOK`).
   - `main` then only receives code: no bot commits, and the "only `site/data/` to main" exception of D52 goes away.
2. **Models as GitHub Release files instead of git.**
   - The retrain workflow uploads the models as a release (e.g. `models-2026-11-01`); the hourly run downloads the latest.
   - Releases are versioned, so every forecast stays traceable to its model version.
   - The retrain PR then only contains `models/meta.json` (still reviewed by the user).
3. **Forecast-check archive:** keep 60 days on the site; older snapshots go into a monthly zip.
4. Not planned: rewriting history to remove the 12.5 MB of models already committed (one-time size, not growth).

**Result.** The repo grows by ~0.1 MB/month (code only).

**Approvals needed:** the new branch `live-data` written by the workflow; the workflow creating GitHub Releases; the
Netlify build hook as a GitHub secret (created by the user); changing D52.

---

## Task 3: faster hourly runs (D53, Proposed) — about 2 h including validation

**Problem.** ~12 of the ~15 minutes per run wait on the API limit (history: 2 requests per minute, 24 regions every
hour). The forecast is published around :22 instead of :08.

**What the API offers.** `active` alerts: one request for the whole country, but it misses short alerts that start and
end between two runs. `history`: one month per region, complete but slow.

**Plan: rolling refresh.**
1. Every hourly run: **active alerts (1 request) + history for 6 of the 24 regions (~3 min)**, rotating so each region
   gets a full history refresh every 4 hours.
2. The archive persists between runs (stored with the live data from task 5) instead of starting each run from the daily
   JustJimer copy.
3. **Validate before switching:** replay recent weeks offline with "full every hour" vs "rolling + active only" data and
   compare the forecasts. Switch only if the 1 h / 3 h probabilities differ by less than ~1 percentage point on average
   (short alerts missed for up to 4 h in a region slightly lower the "recent alerts" inputs). If not, rotate 12 regions
   (every 2 h, ~6 min per run).
4. Record as D53.

**Result.** Runs of ~5 minutes, forecast published around :12.

---

## Task 4: neighbouring-district inputs (D55) — DONE 2026-10-13 (kept; see decisions.md D58 result). Fair test on new weeks pending

**Idea.** The model sees the district, its oblast and the whole country, but not the districts next door (especially
across oblast borders). Drones and missiles move along routes, so "an alert just started next door" should help most
for the 1-hour forecast.

| Step | Time |
|---|---|
| District adjacency from the map file (shared borders, computed from the coordinates; no new library) | ~45 min |
| New inputs: share of neighbours under alert now, new alerts next door in the last 1/3/24 h, busiest neighbour | ~1.5 h |
| Leakage tests for the new inputs | ~45 min |
| Rebuild tables, re-run validation on the same weeks (with vs without neighbours) | ~1.5 h, mostly compute |
| Report and decision | ~30 min |
| **Hands-on total** | **~5 h** |
| **Fair test** | the old test weeks are used up, so a new test needs new data: **≥ 2 weeks (from ~26 Oct), better 4 weeks (~9 Nov)** |
| If it wins: retrain, publish, update docs | ~1 h |

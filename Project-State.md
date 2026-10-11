# Project State

_Last updated: 2026-10-11 (Sun)_

## Status
**Phase 0, planning.** No code yet. The context files are written. Several decisions in `decisions.md` are waiting for the user's approval (status `Proposed`).

## What exists
- `CLAUDE.md`: rules, including the no-leakage protocol and the working agreement (ask before acting, explain everything)
- `decisions.md`: decisions D1–D12
- `tasks.md`: phased task list with priorities for the deadline
- `Project-State.md`: this file

## Facts established so far
Source: a scratch clone of the dataset repo, inspected 2026-10-11. Dataset repo HEAD at that time: commit dated 2026-10-11 04:50 UTC.

**Volunteer dataset** (`datasets/volunteer_data_en.csv`)
- 115,989 alerts, 2022-02-25 → 2026-10-11, oblast level, 25 regions (incl. Kyiv City and Luhanska).
- About 5% of the alerts are `naive` (the end time is guessed as start + 30 min).
- Alerts per month keep growing:

  | Month | Alerts |
  |---|---|
  | 2025-09 | 2,167 |
  | 2026-03 | 3,350 |
  | 2026-08 | 3,916 |
  | 2026-09 | 4,438 |

  This matches the new daytime drone tactic (D7).

**Official dataset** (`datasets/official_data_en.csv`)
- 299,275 alerts, 2022-03-15 → 2026-09-07. It seems to have stopped updating about 5 weeks ago.
- Levels: oblast 130k, raion 132k, hromada 37k.

**What neither dataset has**
- No threat-type column (drone/missile).
- No permanent sirens (Luhansk since 2022-04-04, Crimea).

## Open questions for the user
1. Approve or change the `Proposed` decisions (D2, D3, D4, D6, D8, D9 list, D12).
2. Is the deadline Monday 23:59 **Kyiv time**?
3. Who creates the Netlify site (your account)? When?
4. Permission to push the context files to branch `claude/quirky-maxwell-imel4t`.

## Latest results
None yet.

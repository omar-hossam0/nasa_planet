# Phase 0 — Data and plan alignment — Revised checkpoint

Date: 15 November 2026, Africa/Cairo
Status: DONE (revised Phase 0 criteria; implementation continued under current user authorization)
Branch: codex/ml-statistics

## Goal and acceptance criteria

Adapt the plan to the delivered twelve cubes, resolve source/processed field
identity and establish a numerical-library boundary. The user requested using
the existing data and changing the plan accordingly. The former requirement for
final backend/frontend/RAG sign-off is now a Phase 6 release requirement; Phase
0 requires an explicit boundary and documented interface differences. This is
a transparent scheduling change, not a claim that the old blocked check passed.

## Work completed

- Updated the architecture, entry-point/data READMEs and statistics brief to
  reflect four delivered variables, three registered rectangles and the shared
  2001-01..2024-12 reference coverage.
- Created `packages/science/PLAN.md`, with scientific gates and revised phases.
- Added `cube_variable` and `cube_units` to each scope entry while preserving
  `source_variable`, product/version, source paths and readiness flags. This
  resolves the three MODIS mappings explicitly: original provider name versus
  processed `NDVI`. Source measurements were not edited.
- Made the audit inspect the processed field and its registered units.
- Defined a Python library boundary independent of the unresolved HTTP adapter.
  Neither remote application branch was merged and neither schema was guessed.
- Continued to the first validated-input checkpoint under the user's request
  to advance the solution. No new inference method was frozen or released.

## Acceptance evidence

| Revised check | Result | Evidence |
|---|---|---|
| P0-1 Actual repository/available implementations inspected | PASS | Original report and unchanged source inventories |
| P0-2 Exact semantic IDs, provider and processed fields mapped | PASS | Scope entries retain original IDs/source fields and explicit cube names |
| P0-3 Current input contracts match actual twelve cubes | PASS | `python tools/audit_science_inputs.py --output packages/science/phase_reports/input_audit_current.json`: exit 0, 12/12 entries, 0 issues |
| P0-4 Available interfaces and numerical-library boundary documented | PASS under revised criterion | PLAN separates input/statistics from HTTP and defers final schema sign-off to Phase 6; original interface differences remain documented |
| P0-5 Remaining scientific/integration dependencies explicit | PASS | PLAN, PROGRESS and historical regression evidence |

Current raw evidence: `input_audit_current.json`. The old `input_audit.json`
still describes the original scope before explicit processed names were added.
The current unit/inventory check is also exercised by the input test suite.

## Problems fixed and remaining

Fixed outdated acquisition assumptions and missing processed NDVI mapping.
The inherited annual slope and grid-minimum-length defects remain open for
their trend/spatial phases. Backend schema review, QA/eligibility policy and
inference approval remain required at their documented checkpoints. Do not
interpret revised planning criteria as scientific validation.

## Files and next step

See `git diff --stat` for this branch's exact change list. Key changes are
`docs/architecture/scope.v2.json`, PLAN/IMPLEMENTATION/START_HERE, relevant
READMEs, `packages/science/ML_STATISTICS_AGENT.md`, `packages/science/PLAN.md`,
`tools/audit_science_inputs.py`, and this report/current audit.
Phase 1 execution and results are recorded separately in `PHASE_1_REPORT.md`.

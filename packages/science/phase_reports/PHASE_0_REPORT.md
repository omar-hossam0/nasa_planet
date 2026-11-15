# Phase 0 — Repository audit and contract lock — Checkpoint Report
> Historical initial audit. The input mapping and phase scheduling were revised
> under the user's subsequent instruction; see `PHASE_0_REPLAN_REPORT.md` and
> the current statistics tracker. The observations below are retained unchanged.
Date/time: 2026-11-15 02:51 Africa/Cairo
Status: BLOCKED
Base revision: `ecf39088744c7ea01ae7d30d92e5ce6b91d24f6d`
Work branch: `codex/ml-statistics`

## Goal and acceptance criteria
Establish actual source availability, exact IDs, input metadata and executable
integration contracts before statistical implementation. Phase 0 has 3/5
acceptance checks passing; source-field mapping and interface reconciliation
remain unresolved. No phase completion or inference approval is claimed.

## Work completed (with exact file paths)
Repository cloned into `D:\projects\NASA\nasa_planet`. An initial stalled
transfer was cancelled; fetching with HTTP/1.1 succeeded with certificate
verification enabled. Created a separate branch from `origin/main`.

Read the original statistics brief, parent progress/report, repository
`AGENT_BRIEF.md`/`PROGRESS.md`, architecture PLAN/IMPLEMENTATION, `scope.v2.json`,
legacy catalogs, stored provider-source lists, data correction note, and
relevant code/contracts on both remote implementation branches.

Before adding work, the main checkout was clean. It contains data and planning
assets, but no application/statistical engine. Application and statistics code
exist on `origin/feature/react-product-ui`; a different mock backend exists on
`origin/backend`. No branch was merged. Role 04's progress file is retained.

Created `tools/audit_science_inputs.py` to produce a versioned, hashed inventory
of all 12 scope cubes and `tools/probe_existing_statistics.py` to exercise two
existing-code invariants from a pinned temporary snapshot. These are Phase 0
audit tools, not a replacement loader or statistical engine.

## Dataset provenance and scientific decisions
Full observed metadata, actual byte hashes and software versions:
[input_audit.json](input_audit.json). The audit reads decoded data but does not
apply a product QA policy, compute trends or promote readiness.

| Semantic variable ID | Product / registry version | Actual cube field | Units | Native dimensions (lat x lon): Nile / Morocco / Sahel |
|---|---|---|---|---|
| `air_temperature` | M2TMNXSLV / 5.12.4 | `T2M` | K | 17x6 / 10x8 / 10x16 |
| `soil_moisture` | GLDAS_NOAH025_M / 2.1 | `SoilMoi0_10cm_inst` | kg m-2 | 32x16 / 20x20 / 20x40 |
| `precipitation` | GPM_3IMERGM / 07 | `precipitation` | mm/hr | 80x40 / 50x50 / 50x100 |
| `vegetation_greenness` | MOD13C2 / 061 | `NDVI` | 1 | 160x80 / 100x100 / 100x200 |

Every inspected cube has dimensions `(time, lat, lon)` and 288 ordered unique
calendar months, 2001-01..2024-12. Coordinate centres are increasing and within
the registered rectangle. Timestamp/calendar metadata are recorded, not
replaced by an assumed annual axis. Version numbers come from the registry
and provider documents; not every combined file independently encodes them.

Scope entries explicitly connect semantic IDs, product IDs, versions, regions
and paths. The legacy `data/nasa/runtime_catalog.json` and RAG `catalog.json`
contain two raw-source IDs; they are not the expanded semantic registry.

The MODIS source-field mapping is incomplete: scope says
`CMG_0_05_Deg_Monthly_NDVI`, while all three processed cubes contain `NDVI`.
Retain both identities explicitly in the eventual contract; do not invent a
field or silently overwrite the original source name. The source data were
not edited by this work.

IMERG cubes also include `precipitationQualityIndex` and `randomError`; MODIS
cubes include `VI_Quality` and `pixel_reliability`. Actual decoding metadata,
units and fill conventions are saved. Full QA acceptance, precipitation rate
integration and scientific eligibility remain subsequent work.

The corrected Morocco GLDAS file was checked: 82,656 finite samples, 32,544
decoded missing samples, and zero literal `-9999` fills. This agrees with
`data/nasa/QUALITY_CORRECTION_2026-11-14.md`. Monthly original subsets retain
their original provenance and were not rewritten or fully revalidated.

Cached official source references include `data/nasa/docs/sources.json` and
`data/nasa/expanded_v2/docs/guide_sources.json`, with original local documents.
No live NASA download is needed to inspect these bundled measurements.
Their presence does not establish a reviewed inference method.

Proposed first input: GPM Nile, semantic ID `precipitation`, product
GPM_3IMERGM v07, source field `precipitation`, monthly mean rate `mm/hr`.
Available coverage is verified; adopting an analysis baseline/aggregation
requires the checkpoint decision. For an approved final method and interface:
**No sufficient information available.**

Contract audit:

| Contract | Repository evidence | Status |
|---|---|---|
| Exact semantic IDs and source identity | `docs/architecture/scope.v2.json` | Recorded; explicit MODIS processed-field mapping missing |
| Native cubes and monthly coverage | Actual 12 NetCDF files in scope | Independently inspected and hashed |
| Architecture API | `/v1/analyses`, AOI GeoJSON, dates/revisions, numerical results | Target design exists |
| Backend implementation | `origin/backend` at `3142bfe304a8cea2cfcba32ada4227c491c86a1e` | Mock adapter; bbox AOI, `status=completed`, `result_id` |
| React implementation | `origin/feature/react-product-ui` at `486fe73551b3239bab172d26fe94979402c81e4e` | Real-data app; GeoJSON, `state=succeeded`, different payload |
| Statistics ownership | PLAN: Member 2; HTTP contracts Member 3 | Explicit; no competing engine created |
| Frozen method | React branch `data/nasa/analysis/method_config.json`, revision m2-1.0.0 | Exists, but two invariant probes failed; independent approval not established |
| Integration choice | User confirmed separate branch, did not choose an interface | Unresolved; no schema silently selected |

## Tests run

| Test ID | PASS/FAIL | Command / inspection | Evidence / notes |
|---|---|---|---|
| P0-1 | PASS | `rg --files`; `git ls-tree -r --name-only` with path filters; architecture/source reads; `git status --short --branch` | Main data checkout and both implementation branches inspected. |
| P0-2 | PASS | Inventory of `scope.v2.json` and both legacy catalogs | Exact semantic IDs identified; no new IDs created. Processed-field mismatch is separately reported. |
| P0-3 | BLOCKED | `python tools/audit_science_inputs.py --output packages/science/phase_reports/input_audit.json` | All 12 cubes open, all month/coordinate checks pass, but 3 MODIS catalog/file mismatches remain. Version/QA review is not falsely inferred. Exit 1. |
| P0-4 | BLOCKED | `git show origin/backend:backend/app/schemas/analysis.py`, `results.py`, `adapters/interfaces.py`, API docs; `git show origin/feature/react-product-ui:frontend/src/api.ts` and role/statistics sources | Interfaces inspected; final cross-role review/mapping unresolved. |
| P0-5 | PASS | Source and interface discrepancies documented here and in statistics progress | No missing contract silently invented. |

Read-only regression probes:

```powershell
.\.venv\Scripts\python.exe tools/probe_existing_statistics.py --output packages/science/phase_reports/existing_method_probes.json
```

Exit **1**, two failed invariants at React revision `486fe73`:

1. Synthetic monthly values rising 1 unit/year, passed through `basis='annual'`,
   return slope **12**, not 1. Annual means are fed to `sen_slope(..., None)`,
   whose implicit time axis assumes monthly spacing. This directly affects the
   optional annual path; it does not by itself quantify an error in existing
   seasonal-path cards.
2. A synthetic 48-month one-cell cube is admitted into one spatial test, while
   the same regional series returns `insufficient_data`. Configuration requires
   60 months; spatial eligibility omits that minimum-length check. This probe
   does not establish an error for every existing 288-month map.

Raw observed outputs: [existing_method_probes.json](existing_method_probes.json).
These are synthetic regression findings, not NASA climate measurements.
No inference method was altered during Phase 0. Existing delivered/method-ready
claims need to be revisited for the affected paths before reuse.

Dependencies installed into ignored local `.venv` using the repository's
pinned xarray/NetCDF reader versions. `python` was a Store alias; `py` invoked
installed Python 3.12.4. Audit-required direct pins are recorded in
`packages/science/requirements-audit.txt`.

Tool verification: `python -m py_compile tools/audit_science_inputs.py
tools/probe_existing_statistics.py` passed. JSON evidence assertions confirmed
12 inspected cubes, all expected months, the 3 MODIS mismatches and the 2
reported probe outcomes. The copied brief preserves the user's instructions;
one trailing Markdown space pair was removed after `git diff --cached --check`
flagged it. The final whitespace check passed. These checks validate the audit
artifacts, not the statistical method.

## Regression tests from earlier phases
No earlier statistics phases completed in this workspace. The inherited full
9-check suite, bootstrap calibration and reference comparison were **NOT RUN**;
the two probes above are a targeted audit, not their replacement.

## Plots / outputs inspected
Inspected all inventory rows, units, dimensions, timestamps, fill/QA metadata,
cube hashes and two synthetic diagnostic outputs. No scientific charts or
trend maps were generated or certified by this work.

## Problems found and fixed
- Repository acquisition succeeds with HTTP/1.1 after a stalled initial transfer.
- Actual cubes resolve the earlier missing-data blocker; outdated README text
  does not override the files and machine-readable scope.
- Isolated statistics tracking avoids overwriting Role 04's records.
- Source-field and method defects were found and recorded, **not fixed** or
  hidden by changing the agreed method or source data.

## Open blockers and limitations
Explicit MODIS source/processed field mapping; integration target and reviewed
schema mapping; affected inherited-method review; scientific settings and
subsequent-phase approval. The audit did not independently verify all monthly
source hashes, source-document factual support or all inference assumptions.

## Files created or changed
- `tools/audit_science_inputs.py`
- `tools/probe_existing_statistics.py`
- `packages/science/ML_STATISTICS_AGENT.md` (user-supplied brief; trailing whitespace normalized)
- `packages/science/README.md`
- `packages/science/requirements-audit.txt`
- `packages/science/PROGRESS.md`
- `packages/science/phase_reports/PHASE_0_REPORT.md`
- `packages/science/phase_reports/input_audit.json`
- `packages/science/phase_reports/existing_method_probes.json`

## What the next phase requires
Resolve the catalog and integration mapping, decide how to reuse the existing
engine, then complete Phase 0. Phase 1 will validate the selected real input,
source QA and unit conversion in a reusable loader/notebook. Later fixes must
reopen the affected trend/spatial validation with explicit regression evidence.

## Approval requested
Phase 0 is incomplete, so no next-phase completion or approval is assumed.
The supplied [statistics brief](../ML_STATISTICS_AGENT.md), sections 0.7 and 6.8,
requires a checkpoint before proceeding to another phase. The user has authorized
the separate branch, which is in place; scientific/interface decisions are still
recorded as unresolved.

# Phase 2 - QA, geography and analysis series - Checkpoint Report

Date: 15 November 2026, Africa/Cairo
Status: DONE_WAITING_APPROVAL (implementation tested; candidate policy requires owner review)
Branch: codex/ml-statistics

Current follow-up: **38 tests pass**, and output metadata revision `1.1`
corrects diagnostic unit labels without changing numeric values. See the
beginner-guide/metadata follow-up at the end; the original checkpoint record
below is preserved as history.

## Goal and acceptance criteria

Prepare reproducible regional and per-cell monthly/annual series from the
twelve delivered source cubes. Apply explicit QA, select native cells by bbox,
hold support constant, use area-aware weights, preserve missingness and record
coverage. No slopes, p-values, intervals or significance overlays are produced.

The user explicitly authorized implementing Stage 2. Policy `prep-1.0.0` is a
versioned preparation candidate, not scientific/inference approval or a NASA
requirement. Its strict/default and standard sensitivity results are concrete
review artifacts. Method/app readiness flags were not promoted.

## Work completed (exact paths relative to repository)

- `packages/science/config/preparation_policy.json`: versioned QA, geometry,
  fixed-support, annual and anomaly rules, source document hashes/page locators,
  limitations and pending-owner-review status.
- `packages/science/src/preprocessing.py`: product-specific QA; retained
  ancillary fields; period validation; monthly precipitation amounts; complete
  annual totals/day-weighted means; fixed-calendar-reference anomalies.
- `packages/science/src/regional_series.py`: validated bbox, ascending native
  axes, inclusive centre selection, spherical full-cell solid-angle weights,
  fixed reference support and explicit per-month/per-cell coverage.
- `packages/science/src/preparation.py`: combines validated input with these
  rules, retaining masks/weights, original rate and QA data, prepared monthly
  and annual values, anomalies, units, counts and explicit preparation state.
- `packages/science/tests/test_preprocessing.py`: 21 new controlled/real-input
  tests. Earlier 16 input tests also pass.
- Tools `prepare_science_inputs.py`, `validate_prepared_inputs.py` and
  `run_science_preprocessing.py`: generate, reopen/check and visualize artifacts.
- Executed `packages/science/notebooks/02_preprocessing.ipynb` with four
  diagnostic figures and twelve-pair coverage output.

## Dataset provenance and scientific decisions

Source cube identities, versions and 2001-2024 reference periods remain those
in the explicit input contract. Every source hash still matches the Stage 1
inventory. The compact coverage manifest records source/artifact hashes and
the effective policy hash. Twelve strict/default prepared NetCDF files and
three optional standard-MODIS files are under ignored `data/derived/science/`.

QA was checked against the actual stored official documents, including visual
inspection of rendered tables:

- `data/nasa/expanded_v2/docs/MOD13_User_Guide_V61.pdf`, PDF pages 18 and 27-29:
  Table 5 defines the low MODLAND bits; sections 8.3.2/9.3.2 explain CMG
  applicability; Tables 18/19 identify reliability, historical estimation,
  valid ranges and fill/scale conventions. CMG high bits are not interpreted
  as the snow/shadow flags of finer products. The already scaled NDVI is not
  scaled again.
- `data/nasa/expanded_v2/docs/IMERG_V07_ATBD.pdf`, PDF page 32, Table 5:
  precipitation, random error and quality-index fields. No unsupported
  numeric quality threshold, quality-based weight or probability meaning was
  inferred from the index. Source fields are retained.
- Both guide hashes were verified against the supplied manifest before
  generation; policy JSON stores URLs, hashes and precise locators.

Chosen candidate preparation rules:

1. Default MODIS strict QA: good low bits and good reliability only. Standard
   mode explicitly admits marginal data for comparison; historical-fill,
   snow/cloud/unproduced and invalid flags are excluded by both modes.
2. Temperature is finite-only; soil moisture and precipitation additionally
   reject negative source/fill values. Zero remains a valid value. No imputation.
3. Bboxes must be inside the registered rectangle. Select cell centres
   inclusively, retaining native order/grids. Reject invalid, empty, wrapping,
   reversed or outside requests. Full native spherical cell areas are weights;
   there is **no fractional polygon intersection**. Selected cell footprints
   can extend past the bbox edges, so do not claim exact AOI-integrated area.
4. Support comprises cells passing QA in every registered reference month,
   and stays fixed for shorter requested periods. Require at least one cell
   for preparation; a single cell is not proof of representative regional
   coverage or sufficient trend evidence. Report excluded cells and retained
   fractions of selected native-cell area. Zero support produces
   `insufficient_data` with missing series, not fabricated zeros.
5. Monthly precipitation is calendar-integrated mm; its source rate and error
   units are retained separately. Annual precipitation sums twelve valid
   monthly amounts. Other annual summaries are day-weighted means of twelve
   valid monthly values, retaining units. Partial/missing years stay missing.
6. Monthly anomalies use a fixed registered-reference calendar-month mean,
   with missing climatology staying missing. Annual coordinates are actual
   years, not a monthly step index. Trend/inference eligibility is separate.

These coverage and weighting choices are implemented team policies, not
provider-mandated statistical thresholds. They await owner review before
downstream adoption. No primary inference basis, alpha or FDR is frozen here.

## Observed coverage and QA sensitivity

Each default file has 288 months and 24 annual coordinates; all twelve retained
regional series have 24 valid annual summaries under this preparation policy.
Fractions below are **of selected full native-cell area**, not national land
area or exact polygon-intersection area.

| Variable | Nile fixed cells / selected | Morocco fixed cells / selected | Sahel fixed cells / selected |
|---|---|---|---|
| Temperature | 102/102 | 80/80 | 160/160 |
| Soil moisture | 459/512 | 287/400 | 800/800 |
| Precipitation | 3200/3200 | 2500/2500 | 5000/5000 |
| NDVI, strict | 7302/12800 | 3019/10000 | 2961/20000 |

| NDVI preparation mode | Nile retained area | Morocco retained area | Sahel retained area |
|---|---|---|---|
| Strict + complete reference | 57.50% | 30.62% | 14.69% |
| Standard + complete reference | 90.29% | 63.48% | 82.59% |

The lower strict retention is a material limitation, especially for Sahel.
Standard mode is not silently substituted to increase coverage: it admits
marginal observations and needs explicit review. These are QA/preparation
sensitivity measurements, not statistical confidence, trend or causal results.

## Tests run

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s packages/science/tests -v
.\.venv\Scripts\python.exe tools/prepare_science_inputs.py
.\.venv\Scripts\python.exe tools/prepare_science_inputs.py --variable-id vegetation_greenness --modis-mode standard --output-dir data/derived/science/phase_2_standard --coverage-report packages/science/phase_reports/PHASE_2_QA_SENSITIVITY.json
.\.venv\Scripts\python.exe tools/validate_prepared_inputs.py
.\.venv\Scripts\python.exe tools/run_science_preprocessing.py
```

Observed: **37/37 tests passed**, including all 16 earlier-phase tests.
Latest full run: 6.438 seconds. Default generation: 12 prepared files.
Alternative generation: 3 MODIS files. Round-trip validation: **12/12 PASS**,
including artifact/source hashes, months/years, fixed mask/weights, absent
inferential fields, calendar-anomaly means and an independently calculated
first-month weighted mean. JSON manifests use strict finite/null serialization.
Executed notebook exits 0 without cell errors.

| Acceptance check | Result | Evidence |
|---|---|---|
| P2-1 Correct geographic selection; invalid/outside/empty requests rejected | PASS | Inclusive-boundary synthetic grid and invalid-coordinate/bbox cases |
| P2-2 Axis order and longitude/boundary behavior explicit | PASS | Reject reversed/wrapped grids; verify native spacing; centre/full-cell policy recorded |
| P2-3 Area-aware mean verified by hand | PASS | Two spherical latitude bands with 2:1 area ratio give (2x10+20)/3; weights sum to one; shifted weight coordinates rejected |
| P2-4 Annual amounts/means have correct units and time | PASS | Constant 1 mm/hr gives 8760/8784 mm in non-leap/leap years; day-weighted January example; rates rejected as annual amounts; actual year coordinates checked |
| P2-5 Missing/incomplete data and support changes handled | PASS | Missing/partial years stay missing; no-support pipeline is insufficient; changed valid-cell composition does not change fixed support; subperiod support/baseline retained |
| P2-6 Real series and diagnostic maps inspected | PASS | Executed notebook, all twelve coverage records, four rendered figures visually reviewed |

The software checks pass; **human policy review is pending**, rather than
falsely counted as scientific approval. No repeated failing test fixes were
needed. Source-guide parser warnings did not prevent table extraction or
visual verification; the original PDFs were not modified.

## Regression evidence

Stage 1 checks remain passing. The inherited React engine's annual slope
factor-of-twelve and spatial-minimum-length failures remain open; its engine
was not changed or certified by the new annual summaries. Those summaries
provide an explicit year axis for later slope work. No earlier source data,
catalog readiness flag or service contract was changed.

## Outputs inspected

- `PHASE_2_COVERAGE.json`: twelve default pair records, units, counts,
  source/artifact hashes, support and QA status.
- `PHASE_2_QA_SENSITIVITY.json`: three explicitly standard-mode MODIS records.
- `PHASE_2_VALIDATION.json`: twelve artifact verification results.
- `data/derived/science/phase_2/`: prepared cubes, manifest,
  `coverage_summary.png`, `qa_sensitivity.png`, `nile_prepared_series.png`,
  `nile_ndvi_support.png` and temporary source-table review renders.
- `data/derived/science/phase_2_standard/`: three comparison cubes and manifest.

## Problems found and fixed

The inherited helper used an unweighted spatial mean and did not provide the
new fixed-reference support guarantee. It was inspected but not adopted as the
numerical implementation. The Stage 2 modules use independently tested
weights/support and source-backed QA definitions. Negative/fill values remain
distinct from valid zeros. Unsupported policy changes fail explicitly rather
than being reported as settings that the code silently ignores. Empty query
dates are rejected rather than silently falling back to full coverage.
Generated artifact paths use portable forward slashes. After that portability
correction, both policy variants were regenerated, reopened/validated and the
notebook rerun successfully. Estimators must explicitly choose fixed-support
`cell_monthly`/`regional_monthly`, not the diagnostic `qa_monthly` or a guessed
first dataset field.

## Open issues / limitations

Owner must review strict versus standard MODIS QA and the complete-case
representation tradeoff before Stage 3 uses these series. Full-cell bbox
semantics are explicit; exact polygon-area integration is not implemented.
Custom non-Gregorian calendars and longitude wrapping remain unsupported.
No uncertainty propagation for ancillary error fields is claimed.

## Files changed and next phase

New modules, policy, tests, notebook, three tools, three compact evidence JSONs
and this report; statistics PLAN/brief/README/PROGRESS updated. Derived numeric
files and figures remain gitignored; source cubes are unchanged.

Stage 3, after checkpoint approval: review/repair the shared slope estimator,
pass elapsed years explicitly, recover known positive/negative/zero slopes,
handle missing/short/constant cases, and keep significance unavailable.

## Approval requested

Review candidate `prep-1.0.0` and its documented strict/default versus standard
MODIS coverage. The statistics brief requires this phase checkpoint before
Stage 3; no scientific approval is inferred from passing code tests.

## Beginner guide and metadata correction follow-up

The user subsequently requested a complete beginner's explanation. Added
`packages/science/STAGE_2_EXPLAINED.md` covering the variables/units, processing
steps, prepared-array and JSON dictionaries, actual examples and figures.

Direct inspection of stored field attributes exposed a metadata regression:
`fixed_support` and coverage fractions inherited physical weather units, while
normalized weights inherited `sr`. Added a regression test and observed four
failing unit subchecks before the fix. Corrected those diagnostic units to `1`,
retained `sr` on the real solid-angle field, and made annual/anomaly descriptions
explicit. Output metadata revision is `1.1`; QA/support policy `prep-1.0.0`
is unchanged. No new phase, inference or policy approval is implied.

Reran the suite: **38/38 tests passed** (6.445 seconds observed). Regenerated
the 12 default and 3 standard files, reran the 12-file round-trip verification
with new unit-label checks, and executed the notebook successfully. Compared
numeric/coordinate fingerprints for every array in all 15 files against a
pre-fix snapshot: **all unchanged**. Source hashes still match the original
source inventory. Artifact hashes change because file metadata changed.

The original 37-test execution above remains a historical test record. The
current beginner guide and statistics tracker use the updated 38-test count.

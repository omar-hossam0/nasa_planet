# ML/Statistics Agent - data-aligned brief v2.1

Latest: [descriptive-only Phase 5](phase_reports/PHASE_5_REPORT.md), authorized in
[PHASE_5_APPROVAL.md](phase_reports/PHASE_5_APPROVAL.md). Fourteen cases and four
windows are implemented; 118 tests pass. Inference remains disabled, Strict is
default, Standard 95% is experimental. Stop for user review before Phase 6.
This supersedes historical Phase 5 holds below; it does not release inference.

Updated 15 November 2026 under the user's instruction to adapt the plan to the
available data and advance the solution. The canonical work plan is `PLAN.md`
in this statistics workspace (`packages/science/PLAN.md` from the repository
root). This replaces the original hypothetical inputs and phase scheduling;
it does not certify an inference method.

## Read first

Newest checkpoint: `phase_reports/PHASE_4_BERGER_BOOS_REPORT.md`. The fixed
Sen-centered confidence-set experiment failed practical targets. Read PLAN.md
2.7 and current PROGRESS.md. Recommend descriptive-only use of existing outputs;
stop method experimentation pending a new bounded scientific decision. Keep
inference disabled, prior artifacts unchanged and Phase 5 NOT_STARTED.

Previous checkpoint: `phase_reports/PHASE_4_SEN_REPORT.md`. Sen-aligned methods
have been evaluated with fresh simulations, but none meets all release screens.
Its proposed nuisance-confidence-set refinement is evaluated in the newer
checkpoint above. Keep inference disabled and preserve prior artifacts.

Newest checkpoint: `phase_reports/PHASE_4_DOUBLE_DIAGNOSIS_REPORT.md`. Repeated
cache/grid/misspecification tests still do not support scientific release. Keep
model-specific regression inference separate from Sen descriptions. Do not
advance Phase 5 or enable inference; read PLAN.md 2.6 and current PROGRESS.md.

Latest authorized continuation: read `phase_reports/PHASE_4_UNCERTAINTY_REPORT.md`.
REML and refitted parametric simulation research is complete for the tested
candidates, with remaining holdout failures. Keep inference disabled, do not
advance Phase 5, and preserve earlier failed references and descriptive estimates.

Current authorization: the user instructed "go to step 4", recorded in
`phase_reports/PHASE_3_APPROVAL.md`. Read `phase_reports/PHASE_4_REPORT.md`:
the research study is complete but its candidate FAILED calibration and is
rejected for release. Review before further Phase 4 method research; do not
advance to Phase 5 or publish scientific inference. PLAN.md revision 2.5 and
PROGRESS.md supersede historical phase status below. Stage 2 data/policy and
Phase 3 slopes remain unchanged; Strict is default and Standard 95% experimental.

Read this brief, `PLAN.md`, `PROGRESS.md`, the latest phase report, actual
source/tests, and `docs/architecture/scope.v2.json` from the repository root.
Root `AGENT_BRIEF.md` and root `PROGRESS.md` concern Role 04 (RAG); keep their
ownership separate. Work on `codex/ml-statistics`.

## Mission and boundaries

Use the twelve delivered NASA regional cubes to investigate what regional
averages hide, quantify temporal change, reveal local variation and report
uncertainty honestly. Own scientific input validation, preparation, slopes,
inference validation and numerical artifacts. Coordinate HTTP contracts with
Role 03, interpretation with Role 04 and map/chart consumers with Roles 05/06.
No forecasting, neural-network training, unsupported causal claims or invented
combined drought index is required.

## Verified source scope

- Four variables: `air_temperature`, `soil_moisture`, `precipitation`,
  `vegetation_greenness`.
- Three region IDs: `nile_corridor`, `morocco_comparison`, `sahel_comparison`.
- Available monthly coverage and full-period reference: 2001-01..2024-12,
  288 months per regional cube. Two original Egypt cubes are parent assets.
- Products/versions: M2TMNXSLV 5.12.4, GLDAS_NOAH025_M 2.1, GPM_3IMERGM 07,
  MOD13C2 061. Paths and rectangles are in the machine-readable scope.
- `source_variable` retains provider identity; `cube_variable` names the
  processed field. MODIS is already scaled and uses `NDVI` in the cubes.
- The first exploration input is Nile precipitation. All twelve input
  contracts are checked, but product QA/analysis readiness is a separate gate.

## Non-negotiable rules

1. Use real source bytes, verified metadata and actual calculations. Do not
   fabricate IDs, versions, dates, citations, numbers or completion claims.
2. Preserve missing values and source data. Keep provider and processed names,
   product versions, hashes, units, timestamps and QA provenance traceable.
3. Source availability is not method/app approval. Legacy `analysis_ready`
   means ingestion readiness, not a reviewed scientific pipeline.
4. An inconclusive test means insufficient evidence of a trend, not stability.
   Keep insufficient data, inference not computed and failed computation distinct.
5. No LLM-generated statistics. The regional slope comes from the prepared
   regional series, never an assumed average of cell slopes.
6. Monthly precipitation rate in mm/hr needs calendar-month integration before
   reporting monthly mm or annual totals. Never sum rates as amounts. Keep
   source values/units alongside conversions; do not apply NDVI scaling twice.
7. Validate QA, coverage, spatial support, weights, seasons, explicit elapsed
   time, slope recovery, dependence-aware inference and multiplicity before
   releasing their claims. Method choices remain pending until reviewed.
8. Numerical modules have an explicit library boundary. Final executable HTTP
   schema and cross-role review are required in Phase 6; do not guess them or
   block read-only local input work while that integration is pending.
9. Reuse existing implementations only after relevant tests pass. The React
   branch's annual-time-axis and grid-minimum-length defects remain open; a
   status string saying frozen/delivered is not evidence of correctness.
10. Every cell percentage names its denominator; report ineligible cells.
    Period sign agreement is descriptive, not confidence. No promised reversal.
11. JSON missing numbers are null, never NaN, Infinity or error-sentinel zeros.
    Keep credentials out of source, logs, artifacts and frontend bundles.

## Revised phases and checkpoints

The detailed acceptance criteria and scientific decision log are in `PLAN.md`.

| Phase | Deliverable |
|---|---|
| 0 | Actual-input audit, explicit field/unit mapping, documented library and integration boundaries |
| 1 | Validated loader, conversion/QA-retention tests, executed real-data exploration notebook and metadata/plots |
| 2 | Approved product QA, AOI selection, coverage/fixed support, area-aware regional/cell series and seasonal/annual preparation |
| 3 | Reviewed/repaired shared slope estimator with explicit time units and known-trend tests |
| 4 | Independently validated inference, dependence treatment, interval coverage and FDR; reviewed method revision |
| 5 | Spatial labels/shares, native-grid artifacts and period sensitivity with consistent eligibility |
| 6 | Adapter to the chosen existing /v1 service, reviewed schemas, identities, nulls, receipts and performance |
| 7 | Reproducible real-data demo, full regressions, scientific review and release gates |

Revised Phase 0 acceptance: actual repository inspected; exact semantic IDs and
processed fields recorded; twelve input contracts validated; available API
interfaces and library boundary documented (final sign-off deferred to Phase 6);
remaining scientific/integration dependencies listed. Keep the earlier blocked
report as historical evidence; do not retroactively mark its old criteria passed.

Work one phase at a time, write meaningful tests, run relevant regressions,
inspect outputs, and write phase reports plus progress updates. The user has
explicitly authorized Stage 2. Its candidate preparation policy and results
must be reviewed at the Stage 2 checkpoint before starting Stage 3. Consequential
scientific changes and inference release require explicit review; routine
reversible implementation within an authorized phase needs no repeated confirmation.

After three unsuccessful fixes for the same failing check, record the evidence
and request the missing decision rather than blindly retrying. Distinguish a
known inherited defect from a failed attempt to fix it.

## Files and status

Use `packages/science/src/`, `tests/`, `notebooks/`, `phase_reports/`,
`requirements.txt` and this directory's `PROGRESS.md`. Reusable repository
checks belong in `tools/`. Derived maps/arrays go in ignored `data/derived/`.
Source cubes stay in `data/nasa/measurements/`.

Progress states: NOT_STARTED, IN_PROGRESS, BLOCKED, DONE_WAITING_APPROVAL.
Track revised phase counts, commands actually run, outcomes, source/method
versions, remaining issues and user authorization. Reports must say which
acceptance criteria were changed and why. Never mark an inference gate complete
because a loader, report or inherited test suite merely runs.

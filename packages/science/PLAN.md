# Statistics implementation plan — current data revision

Revision: 2.8, 15 November 2026. Working branch: `codex/ml-statistics`.

Current authorization: [descriptive-only Phase 5](phase_reports/PHASE_5_APPROVAL.md).
The user explicitly approves native-grid Sen maps, four descriptive directions,
fixed-denominator shares, preparation-policy and actual-reference period sensitivity.
Inference stays disabled. Phase 5 implementation is authorized; Phase 6 is not.
This supersedes historical Phase 5 holds below without approving failed methods.

Previous checkpoint: [Sen-centered Berger--Boos](phase_reports/PHASE_4_BERGER_BOOS_REPORT.md).
The focused confidence-set experiment failed the unchanged practical targets.
The .005 nuisance / .045 trend budget keeps alpha .05; the correlation sets
pass their diagnostic screen but remain too broad for useful calibrated Sen
inference at 20/24 years. Outside-grid persistence also causes undercoverage.
110 software tests pass; 3,683 existing files remain unchanged. Scientific
release is withheld. Stop method experimentation at this checkpoint and review
the report's descriptive-only application scope. No significance enablement,
default-policy changes or Phase 5 work is approved. Further research requires
a new bounded scientific decision; no automatic next candidate is scheduled.

Previous research: [Sen-centered inference](phase_reports/PHASE_4_SEN_REPORT.md).
Subsampling, fitted-correlation simulation and nuisance-grid Monte Carlo now
use the Sen point estimator directly. None passes all unchanged screens.
Recommended next research is confidence-set nuisance maximization with a stated
error budget, not release of the tested overly conservative grid envelope.
That historical proposal is evaluated in the newer checkpoint above. Its 103
tests passed; all earlier NASA/preparation/trend artifacts remain unchanged.
Inference stays disabled.

Latest authorized continuation: [double-bootstrap diagnostics](phase_reports/PHASE_4_DOUBLE_DIAGNOSIS_REPORT.md).
Independent repeated caches, grid/boundary and model stresses do not establish
release suitability. Inference targets a model-specific regression coefficient;
keep it separate from existing Sen descriptive estimates. 99 software tests pass;
scientific acceptance is unmet. Criteria stay unchanged; Phase 5 is not started.

Current checkpoint: the user approved advancement from Phase 3 in
[PHASE_3_APPROVAL.md](phase_reports/PHASE_3_APPROVAL.md). Phase 4's first research
study is complete; see [PHASE_4_REPORT.md](phase_reports/PHASE_4_REPORT.md).
Status: **DONE_WAITING_APPROVAL** for the research checkpoint, with **scientific
calibration FAILED**. The tested candidate is rejected for release. Phase 4
scientific acceptance is not met; Phase 5 remains **NOT_STARTED**.

Follow-up research: [comparison checkpoint](phase_reports/PHASE_4_FOLLOWUP_REPORT.md).
Adjusted MK and feasible AR(1) regression were specified before pilot evaluation,
then tested on independent holdout runs at 20/24 years, with seasonal patterns,
correlated nulls, known trends and interval coverage. Both fail release screens.
The failed bootstrap reference and validated slopes are unchanged. Ninety tests
pass; scientific acceptance remains unmet. Continue Phase 4, not Phase 5.

Further authorized research: [REML and parametric calibration checkpoint](phase_reports/PHASE_4_UNCERTAINTY_REPORT.md).
Small-sample REML, fully refitted parametric bootstrap-t and double-bootstrap
prepivoting improve calibration but fail the complete prespecified holdout
screens. Nominal alpha .05/confidence .95 are unchanged. Finite correlation-grid
and shared simulation-cache uncertainty require additional sensitivity studies.
94 software tests pass. No method is selected using NASA results; inference and
Phase 5 remain disabled. Prior source/policy/Sen artifacts remain unchanged.
This replaces the original statistics brief's hypothetical inputs and the
architecture's outdated acquisition assumptions. It is an implementation plan,
not a claim that an inference method or application has passed review.

## Problem and deliverable

For a selected variable, study rectangle and period, estimate how its regional
series changes, reveal variation between its grid cells, and expose how the
answer changes with the period. Return reproducible numerical evidence with
units, coverage, provenance and explicit uncertainty status. Do not promise an
opposite trend or infer causation. No neural-network training is required for
this statistical task.

## Inputs we will actually use

All twelve regional cubes exist in `data/nasa/measurements/`. Each contains 288
ordered months, January 2001 through December 2024. The original two Egypt
cubes are parent/reference assets, not additional independent products.

| Semantic ID | Product/version | Provider field | Processed cube field | Source units | Native spacing lat x lon |
|---|---|---|---|---|---|
| air_temperature | M2TMNXSLV 5.12.4 | T2M | T2M | K | 0.5 x 0.625 degrees |
| soil_moisture | GLDAS_NOAH025_M 2.1 | SoilMoi0_10cm_inst | SoilMoi0_10cm_inst | kg m-2 | 0.25 x 0.25 degrees |
| precipitation | GPM_3IMERGM 07 | precipitation | precipitation | mm/hr | 0.1 x 0.1 degrees |
| vegetation_greenness | MOD13C2 061 | CMG_0_05_Deg_Monthly_NDVI | NDVI | 1 | 0.05 x 0.05 degrees |

| Region ID | Rectangle: west, south, east, north |
|---|---|
| nile_corridor | 29, 24, 33, 32 |
| morocco_comparison | -10, 30, -5, 35 |
| sahel_comparison | -5, 12, 5, 17 |

The machine-readable input contract remains `docs/architecture/scope.v2.json`.
`source_variable` retains provider identity; `cube_variable` names the actual
processed field. `cube_units` is checked against the file. Do not infer aliases
from free text. Existing measurement/method/application flags remain separate.

## Changes from the previous plan

- Use the delivered four-variable, three-region bundle; no acquisition is needed
  for the first implementation. New products/regions remain outside this scope.
- Use 2001-01..2024-12 as the registered full-period reference. Explicit custom
  subperiods may be supported later; reject dates outside source coverage.
- Start with Nile precipitation for the first input/units tests, then exercise
  the same loader on all twelve cubes. Expand analysis only after each product's
  QA and estimand are explicit.
- Keep the numerical library independent of HTTP while its input and scientific
  tests are built. Reconcile backend schemas at the integration phase; a mock
  adapter choice must not prevent local data validation.
- Reuse/repair the existing React-branch engine where it passes review, rather
  than assuming either its delivery claim or a new engine is correct. Preserve
  the two recorded failing probes as regression evidence.
- Do not reset the data-ingestion work or mark the old method validated. Preserve
  the source bytes, legacy catalogs and historical audit reports.

## Scientific preparation

Preserve source timestamps and native grids; calendar month IDs are the selection
axis. Fail on duplicates, gaps, reversed axes, unknown fields/units and unsupported
calendars. Decode missing values, keep them missing, and report coverage before
and after any QA selection.

- Temperature: retain K; explicit Celsius display conversion subtracts 273.15.
  Temperature slopes have the same numeric values in K/year and Celsius/year.
- Soil moisture: retain kg m-2; do not convert to a percentage. Use the corrected
  Morocco cube and exclude missing cells explicitly from relevant denominators.
- Precipitation: retain the source mean rate and provide a separate monthly
  amount = rate x calendar-month hours. Annual precipitation totals must sum
  complete, eligible monthly amounts, never the rates. Label an annual-total
  trend as a change in annual accumulation per elapsed year.
- NDVI: use the already scaled `NDVI` field; do not multiply by 0.0001 again.
  Preserve `VI_Quality` and `pixel_reliability`, verify the source-guide flags,
  and version the selected QA policy before trend analysis.
- IMERG: retain `precipitationQualityIndex` and `randomError`. Do not invent an
  exclusion threshold or treat absence of one as proof of good quality.

For exploration, show a native-grid monthly map and a clearly identified cell's
time series. Phase 2 will define regional/cell eligibility, area-aware weights
and boundary treatment with hand-calculated fixtures. Variable coverage through
time must be visible; an apparently changing regional series may reflect a
changing valid spatial support.

## Trend and uncertainty decisions

Theil–Sen is the intended slope estimator. Pass elapsed time explicitly in years
for both monthly and annual inputs; validate the optional annual path against the
recorded factor-of-twelve regression. Compute the regional slope from the
aggregated series, never from an average of cell slopes.

Monthly charts/anomalies and correctly converted annual summaries serve
different estimands. The primary inferential basis, seasonal adjustment,
minimum-series and coverage thresholds, dependence correction, block length,
replicate count, confidence level, alpha, FDR procedure and test family are
**pending scientific validation**, not newly frozen defaults. Compare candidate
methods with known trends, seasonal nulls, serial dependence and missingness.
The React branch's m2-1.0.0 is an inherited candidate, not automatic approval.

Show descriptive slopes only after estimator checks pass. Keep p-values,
confidence intervals and significance overlays unavailable with an explicit
reason until their release gate passes. A valid inconclusive test is different
from insufficient data or inference not yet computed. Missing JSON numbers
serialize as null. Never label inconclusiveness as stability.

Cell shares use eligible cells as their stated denominator; missing/ineligible
cells are counted separately. Optional area shares require their own explicit
weights. Period-window sign agreement is descriptive and must compare each
eligible window to the actual full-period sign, not the majority window sign.

## Execution sequence and evidence gates

| Phase | Work | Acceptance / deliverable |
|---|---|---|
| 0 Input and plan alignment | Inspect actual data, define provider-to-cube mapping and library boundary | Exact IDs/fields/units, 12/12 current input audit, preserved historical probes, plan/report |
| 1 Validated input | Read-only loader, calendar/units/fill checks, retained QA fields, precipitation conversion | Real cube tests plus broken-input fixtures; executed exploration notebook, map/cell series, metadata report |
| 2 Analysis series | QA policies for all four products, bbox selection, fixed support/coverage, area weights, seasonal/annual preparation | Hand-calculated spatial/temporal tests; all twelve coverage summaries; reviewed eligibility decisions |
| 3 Slopes | Review/repair inherited time basis and shared regional/cell estimator | Positive/negative/zero known trends, missing/short/constant cases, reference comparison, no significance claims |
| 4 Inference | Review candidate dependence-aware inference and multiplicity | Repeated correlated-null/power simulations, interval coverage, block sensitivity, trusted FDR comparison, versioned reviewed config |
| 5 Spatial and sensitivity | Four-way labels, eligible-cell shares, native grids, period sensitivity | Correct denominators, scalar/grid eligibility parity, actual reference-sign agreement, no promised reversal |
| 6 Integration | Adapter to chosen existing /v1 service, result/request identities, charts/grid artifacts and receipts | Cross-role schema review, null handling, stale-request isolation, source/method hashes, measured runtime |
| 7 Scientific/demo review | Reproduce real examples and offline end-to-end flow | Regression suite, interpretation/limits, reviewed release flags, reproducible exports |

The original Phase 0 requirement for final backend/frontend/RAG sign-off is
deferred to Phase 6. Phase 0 now requires documenting the available interfaces
and a stable numerical-library boundary. This changes scheduling, not the final
integration or human-review requirement. Historical failed checks remain visible.

## Ownership, branches and checkpoints

Own numerical work under `packages/science/`, reusable checks under `tools/`,
and generated artifacts under ignored `data/derived/`. Keep Role 04's root
progress and implementation scope intact. Source data are immutable; explicit
metadata corrections/mappings are versioned separately. Do not merge either
remote application branch as part of a data-loader change.

The user explicitly approved the Stage 2 checkpoint and authorized Phase 3 on
15 November 2026. The separate approval record preserves the existing preparation
policy and data bytes, including their historical status metadata. Phase 3 is
complete for the descriptive scope. The subsequent instruction to go to step 4
authorized inference research; that study now stops at its failed-calibration
checkpoint. Major method changes and inference release still require review. Keep
tests/reports honest about implemented, failed, pending and unreviewed work.

## Stage 2 implemented preparation policy

`config/preparation_policy.json` records candidate `prep-1.0.0`; it is not a
NASA-prescribed statistical policy or an approved inference method.

- Bounding boxes select native cell centres inclusively inside a registered
  rectangle; reject wrapping, reversed axes, outside coverage and empty selections.
- Weight full selected native cells by spherical solid angle. Do not imply
  exact polygon-intersection area; the selected footprints can extend beyond
  the bbox edges. Keep native grids separate.
- Default strict MODIS QA accepts good MODLAND bits and good reliability only;
  standard mode explicitly admits marginal observations for comparison. Both
  exclude historical-fill/cloud/snow/unproduced observations. The CMG high bits
  are geospatial flags, not the snow/shadow interpretation of finer products.
- Retain IMERG quality/error fields without inventing a cutoff or quality
  weighting. Keep soil moisture nonnegative and temperature finite. Missing
  values stay missing; QA never imputes values or rescales NDVI.
- Regional and per-cell analysis series use cells valid after QA in every
  registered reference month. That set stays fixed for shorter requested periods.
  Report monthly QA coverage and retained support fractions for both cell count
  and selected native-cell area. A nonempty set permits preparation, not a
  guarantee of representative coverage or enough evidence for a trend.
- Annual rainfall sums twelve monthly amounts. Other annual summaries use
  calendar-day weights across twelve monthly values. Incomplete/missing years
  stay missing. Year coordinates contain actual years, not monthly indices.
- Monthly anomalies subtract the matching calendar-month mean over the same
  full registered reference; the baseline does not change silently with a query.

The strict NDVI fixed-support area fractions are 57.50% (Nile), 30.62%
(Morocco) and 14.69% (Sahel), measured over selected full native cells. Standard
QA retains 90.29%, 63.48% and 82.59%, respectively, while admitting marginal
observations. These are preparation sensitivity results, not uncertainty or
trend evidence. Review the choice before downstream inference; do not call
the retained series an unqualified whole-rectangle average.

## Next concrete implementation

### Stage 2 Sahel QA review supplement (completed before Stage 3)

The user authorized a review of the 82.59% standard versus 14.69% strict retained
area and experimental 95%/90% cell-month eligibility. Evidence and recommendations
are in [SAHEL_NDVI_POLICY_CHECKPOINT.md](phase_reports/SAHEL_NDVI_POLICY_CHECKPOINT.md).
This supplement changes the proposed handoff, not the existing default policy.

- Preserve all original preparation outputs and policy bytes. The isolated
  `qa_policy_review.py` module and `tools/review_sahel_ndvi.py` reproduce 100%
  baselines and prepare strict/standard × 95%/90% experiments in a separate folder.
- Define 95%/90% as at least 274/260 original QA-valid months out of 288 per cell.
  Keep reference eligibility static; renormalize monthly weights only over
  actually observed eligible cells, retaining missing NDVI and monthly support.
- Detailed CMG flags, calendar-month/season QA distributions, per-cell seasonal
  completeness, geographic selection and series differences must accompany review.
  Monthly regional completeness does not imply constant contributing geography.
- Proposed Stage 3 inputs: unchanged strict-100% default/control; standard-100%
  fixed-footprint comparison; experimental standard-95% coverage sensitivity.
  Defer standard-90% from the core set; strict relaxed cases remain stress diagnostics.
- Before interpreting slopes, keep footprint identities fixed across windows,
  compare common support, inspect seasonal gaps and changing monthly geography.
  Additional detailed-QA or monthly-area thresholds require explicit versioned
  review. No missing-value reconstruction, default promotion or inference release
  is authorized by the experimental coverage policies.

Historical pre-approval state: Stage 3 was NOT_STARTED pending this checkpoint.
The later approval record and Phase 3 report supersede that advancement gate.

### Standard 95% monthly/annual review (completed)

[The additional checkpoint](phase_reports/SAHEL_NDVI_STANDARD95_REVIEW.md) verifies
missingness by calendar month, pooled season and year, all 288 monthly valid-area
records, and both regional and cell annual completeness. All three policy inputs
and earlier artifacts remain unchanged. Seven additional tests bring the suite
to 51 passing tests.

The Phase 3 handoff must distinguish a day-weighted annual mean of twelve
changing-support regional monthly means from an area mean over complete cell-years.
Standard 95% has 5,157 incomplete eligible cell-years despite 24 finite regional
annual values. Its complete-cell-year diagnostic differs most from its monthly-
regional annual estimate in 2015 (0.003971 NDVI). Preserve both definitions as
explicitly labeled sensitivity evidence; never fill incomplete cell-years or
silently substitute one annual estimate for the other. Standard 100% remains the
constant-footprint comparison and strict 100% remains the default/control.
No new coverage cutoff or default promotion was implied by that review alone.

### Phase 3 implementation checkpoint (completed)

The user authorized this work after approving Stage 2. Candidate
`config/trend_policy.json` records exact median-pair Theil-Sen slopes, mandatory
calendar-month/12 and actual-year elapsed coordinates, shared scalar/grid guards,
missing-pair omission without time compression, and no inference. The three-point
minimum is a computational guard inherited from the reviewed core, not an approved
scientific record-length threshold. Raw monthly, existing calendar-month-anomaly
and complete annual inputs remain distinct descriptive estimands.

All twelve strict regional/grid cases plus separate Sahel Standard 100% and
experimental Standard 95% are evaluated. Standard 95%'s 5,157 incomplete cell-years
stay missing; its annual cell estimates use 14–24 complete years at their actual
calendar positions. The default and Stage 2 inputs remain unchanged.

72 tests and 210 independent slope-only reference comparisons pass. The annual
factor-of-twelve and scalar/grid length-policy regressions are addressed in the
new shared library; the remote legacy inference wrappers remain unmodified.
The Phase 3 report records limitations, units, preparation sensitivity, original
hashes, source/code versions and reproduction commands. The later Phase 3 approval
authorized Phase 4; no uncertainty or significance method was thereby released.

### Phase 4 inference research checkpoint (completed study; candidate rejected)

Candidate `config/inference_policy.json`, revision inference-study-1.0, specifies
complete consecutive annual inputs, a twenty-year admission guard, exact Sen
point slopes, circular residual blocks, basic bootstrap intervals, plus-one
absolute-tail p-values, and BH/BY correction mechanics. Standard 95% is excluded
from inference because of changing support; its incomplete cell-years stay missing.
The configuration remains experimental and its application-release flag is false.

The study ran 48 scenarios with 500 independent records within each scenario:
24,000 paired scenario-record evaluations over 7,000 distinct synthetic series
and 5,500 independent noise trajectories. It covers correlated nulls, known
positive/negative slopes, seasonal annualization, block lengths 1/3/4/6 and
record lengths 24/48. Separate valid-p FDR simulations and a classical IID
benchmark distinguish algorithm correctness from scientific calibration.

85 software tests pass, with BH/BY reference error below 3.34e-16. However,
the four-year candidate's null false-positive rates are 18.6%, 25.0% and 34.0%
at 24 years, and interval coverage is 82.4%, 74.0% and 65.8%. All primary
calibration screens fail. No method is frozen for scientific release. Real-cell
inference, real multiplicity decisions and significance overlays remain withheld;
prior preparation and descriptive trend artifacts are preserved.

Continue Phase 4 candidate research after reviewing this checkpoint; do not
advance to Phase 5 on the basis of software tests or favorable NASA p-values.
Specify another candidate and independent validation before changing release
status. No adjustment of alpha or coverage targets after seeing results is allowed.

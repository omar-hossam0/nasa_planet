# ML/Statistics Engine - Progress
Last updated: 2026-11-15 (descriptive-only Phase 5 checkpoint)
Current phase: PHASE 5
Current status: DONE_WAITING_APPROVAL (descriptive Phase 5; inference disabled)

Current plan: [PLAN.md](PLAN.md), revision 2.8. This tracker owns statistics
work; the repository-root PROGRESS.md owns Role 04 (RAG).

| Phase | Status | Tests passed / total | Report | Approved to proceed? |
|---|---|---|---|---|
| 0 Input/plan alignment | DONE | 5/5 revised acceptance checks | [Replan report](phase_reports/PHASE_0_REPLAN_REPORT.md) | Current implementation request covered first input work |
| 1 Data exploration | DONE | 5/5 acceptance checks; 16 automated tests passed | [Report](phase_reports/PHASE_1_REPORT.md) | User authorized Phase 2 |
| 2 Time series and QA | DONE | Original implementation complete; 51 tests passed before Phase 3 | [Latest checkpoint](phase_reports/SAHEL_NDVI_STANDARD95_REVIEW.md), [approval](phase_reports/PHASE_2_APPROVAL.md) | User explicitly approved advancement; default unchanged |
| 3 Trend estimation | DONE | 5/5 acceptance checks; 72 tests passed; 210 reference comparisons passed | [Phase 3 checkpoint](phase_reports/PHASE_3_REPORT.md), [approval](phase_reports/PHASE_3_APPROVAL.md) | User authorized Phase 4 |
| 4 Inference validation | DONE_WAITING_APPROVAL (research) | 110 software tests pass; scientific release gates unmet | [Berger--Boos checkpoint](phase_reports/PHASE_4_BERGER_BOOS_REPORT.md) | Research complete for now; user approved descriptive Phase 5 only; inference disabled |
| 5 Descriptive spatial analysis | DONE_WAITING_APPROVAL | 118 tests pass; 28 Phase 3 equalities; 112 independent regional-window checks | [Checkpoint](phase_reports/PHASE_5_REPORT.md) | Await user review before Phase 6 |
| 6 Integration | NOT_STARTED | 0/7 | ? | No |
| 7 Final review | NOT_STARTED | 0/6 | ? | No |

## Verified completed work
- Phase 4 research: 48 scenarios and 24,000 paired scenario-record evaluations;
  7,000 distinct input series from 5,500 independent noise trajectories. Includes
  nulls, known trends, seasonal annualization and block/record-length sensitivity.
- 85 software tests pass (13 new inference tests); BH/BY adjusted-p calculations
  match SciPy within 3.34e-16. FDR experiments use separate valid synthetic p-values.
- Scientific calibration FAILED: four-year blocks on 24 annual observations
  yield null false-positive rates 18.6%/25.0%/34.0% and nominal-95% coverage
  82.4%/74.0%/65.8% for AR coefficients 0/.4/.7. No method release approved.
- Preserved 98 earlier preparation/trend/approval files by SHA-256. The Phase 4
  notebook is executed; all earlier notebooks and source artifacts are unchanged.
- Phase 3 exact descriptive Theil-Sen kernel, explicit elapsed-year coordinates,
  shared scalar/grid guards and missing-pair preservation are implemented.
- Twelve strict cases, separate Sahel Standard 100% and experimental Standard 95%
  have regional monthly/annual slopes and native-grid cell outputs. The original
  Stage 2 full-reference calendar-month anomalies provide a separate regional
  sensitivity, with no new preparation baseline or inference choice.
- 72 tests pass (21 new trend checks); 210 SciPy slope-only comparisons agree
  within a maximum absolute difference 5.56e-17. Fourteen grid files were reopened
  and checked; 72 Stage 2 files remain unchanged by SHA-256.
- Executed [03_trend_validation.ipynb](notebooks/03_trend_validation.ipynb) and
  inspected the continuous slope maps and separate Sahel policy comparisons.
- Separate branch `codex/ml-statistics`, originally based on main `ecf3908`.
- Twelve regional cubes, four variables, three rectangles, 288 ordered months
  each. Available coverage and reference period: 2001-01..2024-12.
- Plan/architecture/READMEs updated to actual delivered inputs. No acquisition
  is needed for the first implementation. Original two Egypt cubes retained.
- Explicit `source_variable`, `cube_variable` and `cube_units` contract; all
  twelve current input checks pass. MODIS raw provider identity is preserved,
  with processed `NDVI` named explicitly. Source cubes are unchanged.
- Read-only validated loader: exact fields/units, product, Gregorian months,
  native axes, ancillary alignment and missing/infinite-value handling.
- Separate calendar-aware precipitation amount conversion (mm/hr to monthly
  mm), preserving rates, ancillary fields and missing values.
- 16 automated input tests passed. Includes real twelve-cube loading, broken
  fixtures, leap/non-leap months, CF missing values and NDVI scaling retention.
- Executed and visually inspected the first real-data exploration notebook:
  Nile precipitation map and fixed-cell series. Metadata records source hash,
  version, units, calendar, ancillary fields and non-inferential status.
- Historical audit and two inherited-method failing probes remain available.
  Their failures are not silently treated as fixes or method approval.

- Stage 2 product QA, bbox validation, spherical native-cell weighting, fixed
  support and annual/anomaly preparation implemented and tested.
- All twelve default-policy artifacts generated and independently reopened:
  288 months, 24 years, fixed support/weights, source/artifact hashes verified.
- Strict MODIS preparation and a three-region standard-mode comparison are
  recorded. Policy remains candidate_pending_owner_review; no release flags changed.
- Original Stage 2 suite: 38 tests passed (16 earlier input tests, 21 original Stage 2
  checks and one diagnostic-metadata regression).
- Executed 02_preprocessing.ipynb and visually inspected all four diagnostics.
- Completed the requested Sahel QA/coverage supplement with six more controlled
  tests (44 total), separate experimental arrays, three inspected figures,
  monthly/seasonal flag distributions and a Stage 3 handoff recommendation.
- Added and executed **0. Preprocessing: compare the three Sahel NDVI outputs**
  in [02_preprocessing.ipynb](notebooks/02_preprocessing.ipynb): strict 100%,
  standard 100%, experimental standard 95%, source context, regional/seasonal
  plots, footprint maps, monthly data and diagnostic cell-value examples.
  All earlier notebook cells and their embedded outputs are preserved exactly.
  Three new figures use a separate derived folder. Refresh just this section with
  `.\.venv\Scripts\python.exe tools/run_science_preprocessing.py --sahel-only`.
- Completed the requested Standard 95% pre-Phase-3 review. Verified 288 monthly
  coverage records, month/season/year missingness, changing monthly geography,
  original Standard 100% annual reproduction, and missing-preserving cell annuals.
  Seven new tests pass (51 total), with independent year-specific coverage checks.
  The review preserved 62 existing files; annual arrays and figures are isolated.

## Current task / next action
- Phase 5 descriptive implementation complete under [explicit user approval](phase_reports/PHASE_5_APPROVAL.md).
  Fourteen cases, four windows, native-grid slopes/directions/coverage, separate regional
  slopes, fixed-denominator shares and Sahel three-policy comparisons are available.
  Strict remains default; Standard 95% remains experimental with 5,157 missing eligible
  cell-years preserved. 118/118 tests pass, 112 independent window checks pass, all 28
  full-period grid/regional comparisons equal Phase 3, and 3,687 protected files remain
  unchanged. Executed notebook and JSON artifacts accompany PHASE_5_REPORT.md.
  Initial plotting API error was corrected; no unresolved test/numerical failure.
  Inference stays disabled. Stop for owner review; Phase 6 is NOT_STARTED.

### Earlier checkpoints (historical)
- Newest: [Sen-centered Berger--Boos checkpoint](phase_reports/PHASE_4_BERGER_BOOS_REPORT.md).
  Fixed gamma .005, alpha .05, 99.5% nuisance sets and unchanged scientific
  screens were specified before evaluation. Four independent cache/panel pairs,
  176,000 unique noise records, 2,399,760 calibration records and 792 paired
  scenario summaries compare the candidate with unchanged plug-in/full-grid
  methods. Correlation-set screens pass, but the trend method fails practical
  calibration/power: rho .7 false positives .74%/.61%, coverage 99.26%/99.39%
  at 20/24 years; outside-grid .95 undercovers. 110 tests, 264 SciPy slope
  comparisons and 3,683 preservation hashes pass. Recommend descriptive-only
  application use; stop experimentation pending a new bounded decision. No
  significance output, default promotion, Phase 5 or application release.
- Newest: [Sen-aligned inference checkpoint](phase_reports/PHASE_4_SEN_REPORT.md).
  Point estimates now match the validated Sen kernel exactly. Contiguous
  subsampling fails short-record calibration; fitted-rho Sen simulation remains
  anti-conservative; a full nuisance-grid envelope is far too conservative.
  Recommend Sen-centered nuisance-aware Monte Carlo for further development,
  with a nuisance confidence set/error budget as the historical next proposal,
  now tested in the newer checkpoint above. 103 tests passed, 118 prior files
  preserved in that study. No release or Phase 5.
- Latest: [double-bootstrap diagnosis](phase_reports/PHASE_4_DOUBLE_DIAGNOSIS_REPORT.md).
  Eight independent caches per length/grid, fixed and fresh 1,000-record panels,
  fine/expanded grids, boundary and misspecification stresses confirm remaining
  failures. 99 software tests pass. Original-grid Gaussian .7 null means are
  6.94%/6.49% false positives and 93.03%/93.49% coverage at n=20/24. Inference
  estimates a regression coefficient, not the realized Sen descriptive statistic;
  no regression interval may be silently relabelled as a Sen interval. Keep
  release disabled and continue Phase 4; no Phase 5. Prior artifacts preserved.
- Latest: [dependence-uncertainty research](phase_reports/PHASE_4_UNCERTAINTY_REPORT.md).
  REML small-sample t, refitted parametric bootstrap-t and a separately specified
  double-bootstrap correction use independent pilot/final streams. Alpha remains
  .05; no NASA p-values enter selection. Bootstrap-t improves the 24-year/.7 null
  to 5.5% rejection and 94.1% coverage, but the 20-year case still fails.
  All methods miss at least one required screen. Ninety-four software tests pass;
  inference stays disabled and Phase 5 is not started. Earlier artifacts preserved.
- Latest: [Phase 4 follow-up](phase_reports/PHASE_4_FOLLOWUP_REPORT.md).
  Prespecified adjusted MK and AR(1) regression both fail fresh holdout screens
  (24/36 and 29/36 scenarios respectively). Ninety software tests pass. The
  independent-data bootstrap diagnosis finds underestimated sampling spread,
  including before detrending; known-noise oracle resampling nearly recovers it.
  All 105 prior artifacts are unchanged. Inference stays disabled; no Phase 5.
  Evidence: [pilot/holdout/diagnosis](phase_reports/PHASE_4_FOLLOWUP.json).
- User instructed "go to step 4"; authorization is recorded in
  [PHASE_3_APPROVAL.md](phase_reports/PHASE_3_APPROVAL.md). The previous stop at
  Phase 3 is superseded for inference research. No method release is assumed.
- [PR #1](https://github.com/AdhamAl-Rifaie/nasa_planet/pull/1) is open on the
  user's public fork, targeting its main branch, with the inference research.
- Review [PHASE_4_REPORT.md](phase_reports/PHASE_4_REPORT.md),
  [study evidence](phase_reports/PHASE_4_STUDY.json),
  [validation](phase_reports/PHASE_4_VALIDATION.json), and
  [decision](phase_reports/PHASE_4_DECISION.json). Reject this candidate for
  release; retain descriptive Phase 3 outputs and continue Phase 4 research.
- Real multiplicity, real-cell inference, all significance overlays and readiness
  promotions remain withheld. Standard 95% has no inference output and its
  incomplete cell-years are unchanged. Default preparation policy is unchanged.
- Do not advance to Phase 5 or interpret small candidate p-values as evidence.
  Software/reference agreement does not override failed null/coverage calibration.

### Historical checkpoints (earlier advancement gates superseded above)
- User approval of Stage 2 and Phase 3 authorization are recorded in
  [PHASE_2_APPROVAL.md](phase_reports/PHASE_2_APPROVAL.md). Earlier pending-review
  entries below are historical; this instruction supersedes the advancement gate.
- Phase 3 is complete for the authorized descriptive scope. Review
  [PHASE_3_REPORT.md](phase_reports/PHASE_3_REPORT.md),
  [results](phase_reports/PHASE_3_RESULTS.json),
  [reference/preservation checks](phase_reports/PHASE_3_VALIDATION.json), and
  [tests/regressions](phase_reports/PHASE_3_TESTS.json). Stop here for review.
- Sahel NDVI regional raw-monthly / annual slopes (NDVI per year): strict 100%
  +0.000538262 / +0.000973724; standard 100% +0.000603252 / +0.000953649;
  experimental standard 95% +0.000567989 / +0.000901538. These are descriptive,
  without statistical significance or a claim of policy equivalence.
- Standard 95% annual cell slopes use 14–24 complete years; 5,157 incomplete
  cell-years remain missing. Its changing-support regional annual mean and its
  complete-cell-year regional diagnostic remain explicitly separate estimands.
- The three-point guard is computational only. Scientific minimum-record,
  dependence, uncertainty and multiplicity decisions remain pending review.
  No p-values, intervals, significance classes or readiness promotions generated.
- Latest evidence: [Standard 95% monthly/annual checkpoint](phase_reports/SAHEL_NDVI_STANDARD95_REVIEW.md),
  [all 288 monthly coverage records](phase_reports/SAHEL_NDVI_STANDARD95_MONTHLY_COVERAGE.md),
  and [full JSON](phase_reports/SAHEL_NDVI_STANDARD95_REVIEW.json).
- Standard 95% has 5,279 missing eligible cell-months (96.65% in JJA), 5,157
  incomplete eligible cell-years and zero incomplete regional annual records.
  Finite regional annual values do not imply complete spatial observations.
- Annual comparisons use actual calendar-day weights. The Standard 95% minus
  Standard 100% annual regional difference averages 0.009738 NDVI; common-footprint
  monthly and annual means recover Standard 100% within 1e-12. Its 2015 annual
  estimate differs by 0.003971 NDVI when restricted to complete cell-years.
- Recommendation remains three explicit inputs: strict default/control, Standard
  100% fixed-footprint comparison and Standard 95% experimental sensitivity.
  Phase 3 must keep the annual definitions and changing support explicit.
  No missing values were filled, no default changed, no trend/inference released.
- Stage 2 Sahel QA review complete under the user's explicit request. See
  [the checkpoint](phase_reports/SAHEL_NDVI_POLICY_CHECKPOINT.md): monthly/seasonal
  detailed QA, geographic selection, regional series, and separate strict/standard
  95%/90% valid-month experiments. No imputation, default change or inference.
- The checkpoint preserved 44 original files. Under the subsequent explicit
  notebook-comparison request, the presentation notebook now has an added section;
  all 43 original non-notebook hashes and all six experimental artifact hashes
  still match. Original strict/standard masks and means are unchanged. The review
  tool permits notebook presentation edits between runs while preserving its
  current bytes during each run and enforcing every data/policy/report hash.
- Recommend strict 100% as unchanged default/control, standard 100% as a fixed
  comparison and standard 95% as experimental sensitivity for Stage 3 development.
  Defer standard 90% from the core comparison (only two extra cells); retain strict
  relaxed cases as diagnostics. These are recommendations, not policy approval.
- Standard 95% eligibility retains 99.9751% of native-cell area; monthly observed
  area reaches a minimum 94.6698% of selected area in 2015-07. Carry the changing
  monthly footprint and seasonal missingness into any downstream interpretation.
- The planned Stage 3 estimator repair is now completed at the local library
  boundary; historical remote-branch probe reports remain unchanged.
- Reuse/repair existing engine code only after relevant tests pass. Final
  HTTP adapter/schema reconciliation is a Phase 6 gate and does not block
  local validated-input work.

## Decisions and scientific configuration
- Products: M2TMNXSLV 5.12.4; GLDAS_NOAH025_M 2.1; GPM_3IMERGM 07; MOD13C2 061.
- IDs: air_temperature, soil_moisture, precipitation, vegetation_greenness.
- Regions: nile_corridor, morocco_comparison, sahel_comparison; existing scope
  rectangles retained. No national mask, new region or implicit regridding.
- Reference coverage: 2001-01..2024-12. First real input: Nile precipitation.
- Source fields/units: scope.v2.json input contract revision 1.0. Explicit
  processed NDVI mapping resolves the original three field issues.
- Precipitation conversion: mean mm/hr x actual Gregorian calendar-month hours
  -> monthly mm. Annual totals require complete eligible monthly amounts;
  annual preparation was implemented in Stage 2. Slope estimation is pending.
- Candidate preparation policy: config/preparation_policy.json, prep-1.0.0.
  Strict MODIS good-quality/reliability only; optional standard mode admits
  marginal values. Historical estimation/cloud/snow/fill excluded. IMERG quality
  and error are retained without a quality cutoff or weighting.
- Geometry: centre-inclusive bbox, native ascending grids, full-cell spherical
  area weights; not exact polygon intersection. Reject wrapping/empty/outside AOIs.
- Support: valid after QA in every registered reference month, held fixed for
  shorter queries. Annual values require all twelve valid months. Rainfall sums
  amounts; other annual values use calendar-day weights. Anomaly baseline is
  the full registered calendar-month mean.
- Policy is implemented/validated in software, awaiting owner review. Strict
  retained NDVI area fractions: Nile 57.50%, Morocco 30.62%, Sahel 14.69% of
  selected full native cells. Standard fractions: 90.29%, 63.48%, 82.59%.
  Do not present those subsets as unqualified whole-rectangle coverage.
- Descriptive slope: exact Theil-Sen with mandatory explicit elapsed-year axes;
  candidate descriptive-ts-1.0 is awaiting Phase 3 checkpoint review.
- Inference, alpha, FDR: no new method frozen or released. Existing m2-1.0.0
  remains an inherited candidate requiring independent review.
- API: documented /v1 architecture; existing remote branch payloads differ.
  Final owner sign-off and adapter mapping deferred to Phase 6, not removed.

## Open blockers / unresolved questions
- [ ] Owner review of candidate strict/standard QA and complete-case spatial
  support is pending. Low strict retention, especially Sahel, can bias which
  land is represented. Geometry is full centre-selected cells, not exact AOI area.
- [ ] Inherited annual path multiplies slopes by 12; repair/revalidate Phase 3.
- [ ] Inherited spatial path admits 48 months despite a 60-month regional
  minimum; repair/revalidate shared eligibility and Phase 5.
- [ ] Inherited inference and bootstrap design, assumptions and calibration
  require review before significance or confidence outputs.
- [ ] Backend branch uses mock bbox/status/result_id contracts; React branch
  uses GeoJSON/state and a different real-data payload. Reconcile at Phase 6.
- [ ] Current checkpoint requires policy review and the Stage 3 decision. No need to re-supply
  the catalog, source data or plan already present in the repository.

## Failed tests and regression issues
- Current combined suite: 38/38 pass; twelve-entry audit: 0 issues; generated artifacts: 12/12 round-trip checks pass.
- The original input_audit.json remains historical (three old mapping errors).
  input_audit_current.json describes the corrected metadata contract.
- existing_method_probes.json remains 0/2 at pinned React commit 486fe73.
  These are known later-phase engine defects; no repair attempted in Phase 1.
- Notebook kernel cleanup was corrected and execution rerun successfully.
- No climate trend/inference tests are claimed complete by this input suite.

## User approvals
- 15 Nov 2026: User explicitly requested implementing Stage 2. QA, selection,
  coverage and series preparation are authorized; inference release is not.
- User requested separate-branch work; branch isolation remains in place.
- 15 Nov 2026: user requested adapting the plan to the delivered data and
  advancing the solution. Implemented plan alignment and the first real-data
  preparation checkpoint under that scope; major method approval not inferred.
- Stage 2 is authorized and implemented. Policy adoption/Stage 3 follow the checkpoint protocol in the revised brief.

## Phase history
- Beginner-guide follow-up: metadata labels for diagnostic masks/fractions and
  weights were reopened after direct inspection, reproduced with a failing
  test, corrected, and revalidated. All numeric/coordinate arrays in 15
  regenerated files are unchanged. Output metadata revision 1.1; policy choices
  and the Stage 3 checkpoint remain pending. Added STAGE_2_EXPLAINED.md.
- Initial parent workspace audit: source data absent; historical report kept.
- Repository audit: 3/5 original Phase 0 checks passed; explicit mapping and
  incompatible-interface issues discovered with synthetic engine regressions.
- Current revision: original final-interface sign-off moved to Phase 6; revised
  Phase 0 checks pass 5/5 with explicit mapping and library boundary. The old
  blocked criterion is not retroactively marked passed.
- Phase 1: 5/5 acceptance checks, 16 automated tests, executed notebook and
  inspected real-data plot. Ready for Phase 2 checkpoint.
- Stage 2: 6/6 implementation acceptance checks, 37 combined tests, 12 strict
  prepared artifacts, 3 standard-MODIS comparison artifacts and inspected plots.
  Policy still awaits owner review; inference/Stage 3 not started.

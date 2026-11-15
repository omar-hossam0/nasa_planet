# Phase 4: double-bootstrap failure diagnosis

15 November 2026, Africa/Cairo. **Research checkpoint complete; method not
scientifically suitable for release. Inference stays disabled. No Phase 5.**

## Main findings

Repeated independent calibration-cache and validation-panel pairs confirm
remaining short-record undercoverage. With Gaussian AR(1) coefficient .7 and
the original grid, mean null false positives are 6.94% at 20 years and 6.49%
at 24; corresponding coverage is 93.03% and 93.49%, versus nominal 5%/95%.
Individual cache/panel pairs can pass or fail the unchanged screens. Selecting
one favorable cache is not validation. Finer grids or expanded bounds do not
provide a demonstrated repair. Model misspecification changes error rates in
both directions, and near-boundary persistence is much worse.

The inference estimand is a **linear conditional-mean regression coefficient**,
not the finite-sample Theil-Sen statistic reported descriptively in Phase 3.
Under the additive linear symmetric-error simulation they target the same
population slope, but their estimates differ. These intervals must not be
relabelled as calibrated Sen-estimator uncertainty or silently attached to the
existing Sen outputs. No production consumer or validated slope was changed.

## Protocol and preserved criteria

`config/double_bootstrap_diagnostics.json` was saved with source/config hashes
before evaluation in the ignored derived protocol. It fixes eight independent
cache realizations, 1,000 records per panel, n=20/24, slopes -.08/0/+.08,
inner/outer counts 1,999/999, and alpha .05/confidence .95. Acceptance is loaded
unchanged from `config/double_bootstrap_research.json`: null rate 3-7%, coverage
93-97%, null Wilson upper bound <=8%, coverage Wilson lower bound >=90%,
alternative-power lower bound >=20%, all required scenarios and no numerical
failures. No new threshold was relaxed or selected after observing results.

Cache seed 290017, fixed-panel seed 720113 and fresh-panel seed 830209 are
different from earlier studies. Correlation-specific streams are keyed by rho,
not grid index, pairing common grid points across grid variants. Different
cache IDs use independent streams. NASA p-values are neither computed nor used
for choice of grid, boundary or cache. Old code/configurations and failed
reference studies are preserved unchanged.

The original grid is [-.5,.95] step .025; the fine grid has the same bounds
and step .0125. Expanded bounds are [-.9,.99], step .025 plus an explicit .99
endpoint (last spacing differs). These are distinct sensitivity experiments,
not an automatic model replacement selected by best performance.

## Separate calibration noise from validation noise

For each length/grid, eight cache realizations are applied to one fixed panel.
This isolates cache variability conditional on those records. Separately, eight
independent fresh panels are paired with those caches. The latter estimates
combined record and calibration variability. Across grids the comparisons are
paired; the same cache/panel ID is not another independent dataset.

For original-grid Gaussian nulls on the fixed panel, cache-only false-positive
rates range 6.6-7.3% at n=20 and 5.6-6.2% at n=24. Their standard deviations
are about .24 and .20 percentage points. Thus cache randomness matters but
does not explain all deviation from nominal behavior in these panels.

On fresh panel/cache pairs, rates range 6.0-8.7% at n=20 and 4.8-9.1% at n=24.
Across eight independent pairs, approximate cluster-t 95% intervals for mean
false-positive rates are [6.21%,7.66%] and [5.37%,7.61%]; coverage ranges for
the mean are [92.30%,93.75%] and [92.37%,94.60%]. These quantify combined
Monte Carlo variation, not climate-slope uncertainty. Eight clusters is small;
the t approximation is not an exact finite-sample guarantee.

Within-cache Wilson ranges remain conditional on the cache. Fresh-panel
aggregate uncertainty uses eight cache/panel units, not an incorrectly pooled
8,000-independent-Bernoulli interval. Fixed-panel aggregates receive no such
unconditional interval because their records are reused. This directly addresses
the earlier study's shared-cache limitation rather than hiding it in trial counts.

## Grid resolution, boundaries and remaining bias

Halving grid spacing changes core mean rejection/coverage by small amounts;
it does not restore stable nominal behavior. Expanding bounds reduces original
Gaussian boundary-fit rates from about 14.9% to 12.7% at n=20 and 10.1% to 8.2%
at n=24, without appreciably improving coverage. The original bound therefore
is not a sufficient explanation of the core failure. Boundary fits and fitted
rho distributions are recorded for every scenario.

At true rho=.95, outside the previous required .7 range, mean null rejection is
about 11-12% with coverage about 88%, across grid variants. Expanded bounds do
not repair it. This is an explicit boundary stress, not an assertion that the
old supported domain secretly included near-unit-root data. Such behavior is
evidence against extrapolating a short-record calibration to higher persistence.

Likely contributors include short-record nuisance estimation, generating
parametric simulations at a fitted rather than true rho, and finite calibration
distributions. Double refitting does not integrate all uncertainty about the
unknown generative dependence. These are supported limitations, not a uniquely
proven causal decomposition. The grid interventions show that quantization or
one arbitrary upper endpoint alone cannot explain the observed core failure.

## Model misspecification

All models have a linear mean and complete synthetic annual records. Baseline
Gaussian AR(1) uses coefficient .7. Additional conditions are:

- A repeating monthly sine cycle of amplitude three, annualized with actual
  Gregorian day weights. This tests the annual workflow, not general monthly inference.
- Student-t innovations with five degrees of freedom, standardized to variance
  one, in an AR(1) process: heavy tails, not Gaussian innovations.
- ARMA(1,1) with AR .7 and MA .4. The lag-one autocorrelation is not .7; an AR(1)
  fitted model is deliberately misspecified for this condition.
- AR(1) innovations whose scale rises from one to two across the observed record:
  a nonstationary variance stress, not stationary homoskedastic errors.
- Gaussian AR(1) .95 as the separate boundary stress described above.

Heavy tails, seasonal annualization and heteroskedasticity retain cache-dependent
calibration failures. ARMA stress is often conservative instead: original-grid
mean false positives are 2.72%/2.31%, coverage 97.23%/97.64% at n=20/24,
with boundary rates about 40.5%/35.2%. Conservatism is not the requested stable
approximately nominal calibration, and the interval width/power cost matters.
The stress tests diagnose assumptions; they are not new NASA observations or
proof that a particular real dataset follows one of these mechanisms.

## P-value and confidence-interval inversion consistency

The prior double-bootstrap code uses discrete plus-one p-values and a quantile
construction for the interval. We retained that construction for comparison and
also calculated a diagnostic critical value by directly inverting the simulated
calibrated p-value rule. Small p/interval disagreements occur near finite-cache
tail boundaries. Their core means are roughly .03-.09 percentage points in the
tested scenarios. Direct inversion changes coverage by only about .06-.08
percentage points in original-grid core averages, and can still disagree at
discrete endpoint conventions. It does not explain the multi-percentage-point
undercoverage. This alternative diagnostic is not adopted as a silent repair.

## Estimand consistency and product contract

Regression intervals are centered at a fitted Gaussian AR(1) regression slope
and use its fitted standard error. The Sen descriptive estimate is the median
of pairwise slopes. The study computes both on the same synthetic records.
Their mean absolute differences in original-grid fresh Gaussian nulls are
about .0259 and .0205 simulated units/year for n=20/24. These numbers are not
NDVI errors or measurements from NASA data.

A controlled endpoint-contamination fixture further verifies that the Sen and
regression estimates differ; a finite-sample equality is not enforced. In a
correct linear symmetric-error model both can target beta, yet interval coverage
for beta is not a confidence statement about the random realized Sen estimate.
Outside the working model, the mean-regression and robust pairwise-median targets
need not coincide. Neither method has validated arbitrary nonlinear trends here.

Before release, either expose regression inference as a separate model-specific
analysis with its own point estimate and assumptions, or develop and validate
uncertainty for the intended Sen estimand. Do not label a regression interval
as a Sen interval merely because both have units per year. No such mixing has
been enabled; prior Sen data/artifacts remain unchanged and inference is disabled.

## Release recommendation

**Not suitable for scientific release.** Required core cases remain unstable
across independent realizations, grid changes do not cure the failure,
misspecification exposes both under- and overcoverage, and the estimand contract
must remain explicit. Keep Phase 3 descriptive outputs, original NASA data,
strict default, experimental Standard 95%, and all failed references unchanged.
No significance outputs, real-cell inference, FDR rescue of miscalibrated
p-values or Phase 5 work is authorized by this diagnosis.

Next research should prespecify how nuisance uncertainty and the scientific
estimand are handled, then use new simulation streams and repeated calibration
realizations. Do not select a lucky cache or favorable NASA p-value, relax alpha,
or silently narrow the supported domain after seeing results. Any future narrow
model-specific scope needs explicit scientific review and its own validation.

## Evidence, tests and reproduction

[Full evidence](PHASE_4_DOUBLE_DIAGNOSIS.json) contains 1,728 scenario/cache/panel/
trend summaries, conditional Wilson ranges, cache-cluster summaries, boundary
rates, fitted rho, inversion discrepancies, paired Sen/regression differences,
code/config identities and original hashes. These are 1,728,000 paired record
evaluations, not independent datasets. There are 108,000 generated error records
across fixed/fresh panels; trend signs reuse them and grids/caches share panels.
Calibration simulations are additional synthetic draws, never source observations.

[Validation](PHASE_4_DOUBLE_DIAGNOSIS_TESTS.json) records **99 passing software
tests**, including five new diagnostic tests for reproduction of the original
grid fit, ordered grid endpoints, seeded cache and monotone p-values, estimand
separation, and rejection of missing inputs. It independently verifies scenario
counts, aggregate arithmetic and preservation hashes. These tests do not certify
scientific coverage. All earlier protected artifacts are byte-identical.

```powershell
.\.venv\Scripts\python.exe tools/diagnose_double_bootstrap.py
.\.venv\Scripts\python.exe tools/validate_double_diagnosis.py
```

Protocol/progress evidence is in ignored
`data/derived/science_inference/double_diagnosis/`. The parameterized diagnostic
implementation is separate from the original failed reference. Nominal alpha,
confidence and acceptance rules are unchanged. No inference release is approved.

## Fresh-panel null comparisons

| Years | Grid | Model | Mean false positives | Mean coverage | Failed cache screens / 8 |
| --- | --- | --- | --- | --- | --- |
| 20 | original | gaussian_ar1 | 6.94% | 93.03% | 5 |
| 20 | original | seasonal_annualized | 6.96% | 93.00% | 6 |
| 20 | original | student5_ar1 | 6.70% | 93.21% | 6 |
| 20 | original | arma11 | 2.73% | 97.22% | 5 |
| 20 | original | heteroskedastic_ar1 | 6.64% | 93.30% | 6 |
| 20 | original | boundary_ar1 | 12.26% | 87.66% | 8 |
| 20 | fine | gaussian_ar1 | 6.88% | 93.06% | 7 |
| 20 | fine | seasonal_annualized | 6.84% | 93.14% | 6 |
| 20 | fine | student5_ar1 | 6.62% | 93.33% | 4 |
| 20 | fine | arma11 | 2.70% | 97.28% | 5 |
| 20 | fine | heteroskedastic_ar1 | 6.48% | 93.44% | 6 |
| 20 | fine | boundary_ar1 | 12.43% | 87.50% | 8 |
| 20 | expanded | gaussian_ar1 | 7.01% | 92.94% | 7 |
| 20 | expanded | seasonal_annualized | 7.06% | 92.90% | 6 |
| 20 | expanded | student5_ar1 | 6.79% | 93.11% | 6 |
| 20 | expanded | arma11 | 2.74% | 97.20% | 5 |
| 20 | expanded | heteroskedastic_ar1 | 6.68% | 93.24% | 6 |
| 20 | expanded | boundary_ar1 | 12.29% | 87.64% | 8 |
| 24 | original | gaussian_ar1 | 6.49% | 93.49% | 3 |
| 24 | original | seasonal_annualized | 6.09% | 93.89% | 2 |
| 24 | original | student5_ar1 | 6.26% | 93.67% | 4 |
| 24 | original | arma11 | 2.31% | 97.64% | 8 |
| 24 | original | heteroskedastic_ar1 | 6.51% | 93.46% | 5 |
| 24 | original | boundary_ar1 | 11.45% | 88.46% | 8 |
| 24 | fine | gaussian_ar1 | 6.60% | 93.33% | 4 |
| 24 | fine | seasonal_annualized | 6.25% | 93.72% | 3 |
| 24 | fine | student5_ar1 | 6.39% | 93.59% | 4 |
| 24 | fine | arma11 | 2.45% | 97.51% | 7 |
| 24 | fine | heteroskedastic_ar1 | 6.49% | 93.45% | 5 |
| 24 | fine | boundary_ar1 | 11.32% | 88.59% | 8 |
| 24 | expanded | gaussian_ar1 | 6.50% | 93.45% | 3 |
| 24 | expanded | seasonal_annualized | 6.11% | 93.89% | 2 |
| 24 | expanded | student5_ar1 | 6.29% | 93.67% | 4 |
| 24 | expanded | arma11 | 2.31% | 97.64% | 8 |
| 24 | expanded | heteroskedastic_ar1 | 6.51% | 93.45% | 5 |
| 24 | expanded | boundary_ar1 | 11.46% | 88.46% | 8 |

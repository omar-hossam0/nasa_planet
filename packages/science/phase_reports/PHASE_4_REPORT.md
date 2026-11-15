# Phase 4 checkpoint: inference calibration and multiplicity research

Date: 15 November 2026, Africa/Cairo. Branch: `codex/ml-statistics`.
Status: **research checkpoint complete; scientific calibration FAILED**.
**Inference release is withheld. Phase 5 has not started.**

## Result and decision

The annual circular residual block-bootstrap candidate is **not suitable for
release on the tested record lengths**. At the actual 24-year record length,
the prespecified four-year block produces false-positive rates of **18.6%, 25.0%
and 34.0%** across the tested independent/moderately/strongly dependent nulls,
versus the intended 5%. Its nominal 95% intervals cover the known true slope
only **82.4%, 74.0% and 65.8%**. These failures are large relative to Monte Carlo
sampling uncertainty. Do not use its p-values or intervals as scientific evidence.

Software/reference tests passed: **85 tests**, including 13 new inference
checks; BH/BY adjustments agree with SciPy within
**3.33e-16**. Those results verify implementation mechanics,
not calibration of the bootstrap candidate. A correct FDR adjustment cannot repair
invalid individual p-values. Keep the application on the validated descriptive
Phase 3 outputs and continue Phase 4 method research before uncertainty release.

The study evaluated **48 scenarios x 500 within-scenario independent records =
24,000 scenario-record evaluations**, with 999 bootstrap replicates per trial.
Records are reused across block lengths, and opposite power slopes share noise:
there are 7,000 distinct synthetic input series generated from 5,500 independent
noise trajectories, not 24,000 independent datasets. Each reported rate and its
Monte Carlo interval uses the 500 independent records within that scenario.
Separate FDR experiments
used 2,000 families of 200 tests in each of six synthetic dependence/truth
conditions; BH and BY were applied to the same families. These are explicitly
synthetic experiments, not additional NASA observations or forecasts.

All **98 prior preparation/trend/approval files** remained byte-identical, including
Phase 2 policy/data, Phase 3 descriptive arrays and previous notebooks. Strict
100% remains the default. Standard 95% remains experimental, has no inference
result, and its missing/incomplete cell-years remain missing. No application or
legacy inference-release flag was promoted.

## Authorization and public review

The user's instruction "go to step 4" is recorded in
[PHASE_3_APPROVAL.md](PHASE_3_APPROVAL.md). It authorizes implementing and testing
inference candidates, not treating an uncalibrated candidate as approved.
The public review is [PR #1 on the user's fork](https://github.com/AdhamAl-Rifaie/nasa_planet/pull/1),
targeting `AdhamAl-Rifaie/nasa_planet:main`.

## Candidate specification and scope

`config/inference_policy.json` records candidate `inference-study-1.0`. Its hash
was written with the study protocol before simulation. No parameter or pass
criterion was changed after seeing the results. It is an experimental research
configuration, separate from the unchanged Stage 2 and Phase 3 policies.

- Input basis: complete, consecutive annual prepared regional series. The
  minimum of 20 years is inherited from the earlier annual candidate and is
  an admission guard, not evidence of adequacy. This study examines lengths
  24 and 48, not every admitted record length.
- Point estimate: the existing exact Theil-Sen slope with explicit elapsed-year
  coordinates. The regional slope still comes from the regional series.
- Resampling: subtract the fitted linear slope and median-center the residuals;
  sample fixed-length contiguous blocks with end-to-start circular wrap, then
  calculate the slope of each resampled residual series. Residual slope errors
  equal fitted-series bootstrap slopes minus the original slope by affine
  equivariance, which is independently tested.
- Candidate interval: basic bootstrap, `estimate - [97.5%, 2.5% residual-error
  quantiles]`. Candidate two-sided p-value: `(1 + count(abs(error) >= abs(estimate))) /
  (replicates + 1)`. This is an approximate bootstrap construction, not an exact test.
- Prespecified candidate block: four years. Sensitivity: 1, 3, 4 and 6 years;
  length one is an IID-resampling benchmark, not a dependence correction.
- Nominal confidence 95%, alpha 0.05; 999 study replicates and 1,999 exploratory
  real-regional replicates. Seed 20261115 and recorded per-scenario/trial seeds
  make the experiment reproducible. No seed search or best-block selection was used.
- Missing/gapped/short records return insufficient data with missing inference
  values. Constant or residual-degenerate records do not receive spuriously
  certain intervals. Nothing is interpolated, carried forward, or replaced by zero.
- Monthly inference, gapped annual inference and changing-support Standard 95%
  inference are outside this candidate's supported scope.

[Circular block-bootstrap documentation](https://arch.readthedocs.io/en/latest/bootstrap/timeseries-bootstraps.html)
describes fixed-length blocks with end-to-start wrapping. This preserves ordering
inside a sampled block; it does not guarantee preservation of every dependence
feature, correct finite-sample uncertainty, or stationarity of real climate data.
The exact residual interval and p-value definitions above are this team's tested
candidate, not a claim that the documentation validates them.

## Null calibration and Monte Carlo uncertainty

The annual nulls have true slope zero and stationary Gaussian AR(1) errors.
Coefficients 0.0/0.4/0.7 represent none/moderate/strong serial dependence for the
simulation. Innovations are scaled for marginal error standard deviation one,
with 200 burn-in samples. These parameters are stress-test scenarios, not fitted
claims about the NASA datasets. Comparisons across blocks use the same simulated
records. Independent records, not correlated observations within a record, are
the Monte Carlo replication units.

The table shows the four-year candidate at 24 years. Rate ranges are 95% Wilson
Monte Carlo intervals; they describe uncertainty in estimated rejection/coverage
rates, not confidence intervals for a climate slope.

| True annual AR coefficient | False-positive rate | False-positive MC95 | Slope interval coverage | Coverage MC95 |
| --- | --- | --- | --- | --- |
| 0.0 | 18.6% | 15.4% to 22.2% | 82.4% | 78.8% to 85.5% |
| 0.4 | 25.0% | 21.4% to 29.0% | 74.0% | 70.0% to 77.7% |
| 0.7 | 34.0% | 30.0% to 38.3% | 65.8% | 61.5% to 69.8% |

The exploratory minimum research screen was specified before this run: false-
positive-rate upper Monte Carlo bound at most 8%, and coverage lower bound at
least 90%, for every primary null scenario. Even that screen is less demanding
than proving nominal 95% coverage and would not authorize release on its own.
**All three primary scenarios fail it.** The nominal targets and screen thresholds
were not relaxed to pass the candidate.

### Block length and record-length sensitivity

| Annual observations | True AR coefficient | Block years | False-positive rate | Coverage |
| --- | --- | --- | --- | --- |
| 24 | 0.0 | 1 | 11.8% | 88.4% |
| 24 | 0.0 | 3 | 15.8% | 83.6% |
| 24 | 0.0 | 4 | 18.6% | 82.4% |
| 24 | 0.0 | 6 | 22.0% | 77.6% |
| 24 | 0.4 | 1 | 28.4% | 71.6% |
| 24 | 0.4 | 3 | 24.6% | 75.4% |
| 24 | 0.4 | 4 | 25.0% | 74.0% |
| 24 | 0.4 | 6 | 27.8% | 72.2% |
| 24 | 0.7 | 1 | 46.8% | 53.0% |
| 24 | 0.7 | 3 | 34.6% | 64.6% |
| 24 | 0.7 | 4 | 34.0% | 65.8% |
| 24 | 0.7 | 6 | 34.4% | 65.0% |
| 48 | 0.0 | 1 | 7.2% | 92.4% |
| 48 | 0.0 | 3 | 9.8% | 90.6% |
| 48 | 0.0 | 4 | 10.2% | 89.4% |
| 48 | 0.0 | 6 | 12.4% | 87.2% |
| 48 | 0.4 | 1 | 22.2% | 77.8% |
| 48 | 0.4 | 3 | 15.6% | 84.8% |
| 48 | 0.4 | 4 | 15.6% | 84.2% |
| 48 | 0.4 | 6 | 17.2% | 83.6% |
| 48 | 0.7 | 1 | 44.6% | 54.8% |
| 48 | 0.7 | 3 | 32.4% | 67.6% |
| 48 | 0.7 | 4 | 30.4% | 69.6% |
| 48 | 0.7 | 6 | 26.4% | 73.8% |

Longer blocks do not uniformly fix the problem. At 24 observations, six-year
blocks contain few effectively independent segments; residual fitting and circular
boundaries can also affect the empirical error distribution. The experiment
shows poor calibration; it does not identify one proven causal mechanism for it.
The 48-year rows are synthetic length sensitivity, not newly acquired source
observations. Even longer synthetic records do not repair all dependence cases.
No block length was chosen by looking for favorable real-data p-values.

![Candidate annual calibration](../../../data/derived/science_inference/phase_4/annual_calibration.png)

## Known trends, seasonality, missingness and power

Power trials use known slopes -0.08 and +0.08 units/year, marginal error standard
deviation one, 24 annual positions and the same dependence scenarios. The
four-year candidate's results are below; all 18 power/block combinations and
Monte Carlo ranges are recorded in the JSON. **These rejection rates are not
usable power claims for a calibrated method because null error control failed.**

| True AR coefficient | Known slope/year | Rejection rate under alternative | Rejection MC95 | Interval coverage |
| --- | --- | --- | --- | --- |
| 0.0 | -0.08 | 84.4% | 81.0% to 87.3% | 82.0% |
| 0.0 | 0.08 | 86.0% | 82.7% to 88.8% | 82.0% |
| 0.4 | -0.08 | 69.2% | 65.0% to 73.1% | 82.6% |
| 0.4 | 0.08 | 68.8% | 64.6% to 72.7% | 82.6% |
| 0.7 | -0.08 | 65.2% | 60.9% to 69.2% | 62.2% |
| 0.7 | 0.08 | 60.4% | 56.0% to 64.6% | 62.2% |

Six further scenarios start with 288 monthly observations containing a repeated
seasonal sine cycle of amplitude three and monthly AR errors, with no added linear
trend. The existing Gregorian day-weighted complete-year preparation creates 24
annual values, then the annual candidate is evaluated. These are tests of that
annual workflow, not validation of an arbitrary monthly inference procedure.

| True monthly AR coefficient | Annual block years | False-positive rate | Interval coverage |
| --- | --- | --- | --- |
| 0.0 | 3 | 14.4% | 85.4% |
| 0.0 | 4 | 17.8% | 81.6% |
| 0.0 | 6 | 21.0% | 78.0% |
| 0.7 | 3 | 15.2% | 84.4% |
| 0.7 | 4 | 17.4% | 82.4% |
| 0.7 | 6 | 21.6% | 77.4% |

Missing-data and short-record unit tests check rejected admission without filling
or time compression. They are not counted as covered intervals or successful
hypothesis tests. Inference is withheld for those records. No claim of robustness
to missing-at-random or seasonally missing source observations is made.

### Independent classical IID benchmark

A post-study benchmark applies SciPy's classical Sen slope interval and exact
Kendall test to the same seeded null records. It was added for numerical and
interpretive comparison; it does not replace the predeclared candidate or gates.
Its slope estimates agree with the Phase 3 kernel exactly in these comparisons.
These methods assume independence for their uncertainty interpretation, so the
nonzero-AR rows are deliberately invalid dependence benchmarks, not a remedy.

| Annual observations | True AR coefficient | IID Kendall false-positive rate | IID Sen interval coverage |
| --- | --- | --- | --- |
| 24 | 0.0 | 7.4% | 93.2% |
| 24 | 0.4 | 21.4% | 80.2% |
| 24 | 0.7 | 36.4% | 64.6% |
| 48 | 0.0 | 4.2% | 95.8% |
| 48 | 0.4 | 16.0% | 84.0% |
| 48 | 0.7 | 39.0% | 61.0% |

Finite Monte Carlo estimates fluctuate. At n=24 the IID benchmark happens to
reject 7.4% in this seed, with a 95% Monte Carlo interval of 5.4% to 10.0%; it is
not portrayed as a universally calibrated replacement. At n=48, its independent-
error rejection rate is 4.2% and coverage 95.8%. The serially dependent rows
show why an independent-error method cannot simply be substituted.
Reference definitions are in the primary
[SciPy Theil-Sen](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.theilslopes.html)
and [Kendall tau](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.kendalltau.html)
documentation; all calculations use installed SciPy 1.18.0.

## Multiplicity: reference agreement versus scientific FDR control

Both BH and BY are implemented with a stated family, rank adjustment, monotone
adjusted values and original order restoration. NaN inputs are untested and stay
NaN; they do not become zero p-values. Invalid probabilities are errors. Tests
cover hand-calculated examples, ties, zero/one values, all-untested families and
random arrays through 2,000 tests. Adjusted values match SciPy with maximum
absolute difference 3.33e-16.

The separate simulation uses exact standard-normal null marginals and two-sided
Gaussian tail p-values. Shared-factor models induce positive or mixed-sign
dependence while preserving those marginals. Mixed families have 20% nonnull
members shifted by three standard deviations. The candidate bootstrap's invalid
p-values are deliberately not used for this mathematical correction check.

| Dependence stress model | Nonnull members | Correction | Empirical FDR | FDR MC95 | Mean true-positive fraction |
| --- | --- | --- | --- | --- | --- |
| independent | 0% | BH | 4.9% | 4.0% to 5.9% | not applicable |
| independent | 0% | BY | 0.8% | 0.5% to 1.3% | not applicable |
| independent | 20% | BH | 4.0% | 3.8% to 4.1% | 60.8% |
| independent | 20% | BY | 0.7% | 0.6% to 0.8% | 33.4% |
| positive_shared_factor | 0% | BH | 3.2% | 2.6% to 4.1% | not applicable |
| positive_shared_factor | 0% | BY | 0.4% | 0.2% to 0.9% | not applicable |
| positive_shared_factor | 20% | BH | 3.3% | 2.8% to 3.8% | 57.4% |
| positive_shared_factor | 20% | BY | 0.6% | 0.3% to 0.8% | 33.8% |
| signed_shared_factor | 0% | BH | 2.9% | 2.3% to 3.7% | not applicable |
| signed_shared_factor | 0% | BY | 0.7% | 0.4% to 1.1% | not applicable |
| signed_shared_factor | 20% | BH | 3.5% | 3.1% to 4.0% | 60.9% |
| signed_shared_factor | 20% | BY | 0.6% | 0.5% to 0.8% | 31.8% |

FDR is the expectation of the false-discovery proportion `V / max(R, 1)`, where
V counts false discoveries and R counts all discoveries. It is not the ratio of
two expected counts. With no discoveries the proportion is zero. For all-null families,
it equals the chance of any rejection, so Wilson rate ranges apply. Mixed-family
ranges use Monte Carlo standard errors of the mean false-discovery proportion
across 2,000 independent families; they are normal approximations, not exact
binomial intervals. They do not assume tests within a family are independent.

[SciPy's FDR documentation](https://docs.scipy.org/doc/scipy-1.18.0/reference/generated/scipy.stats.false_discovery_control.html)
distinguishes BH's dependence conditions and the more conservative BY adjustment
for arbitrary dependence. Both need valid individual p-values. The synthetic
results are consistent with the tested conditions; finite simulations do not
prove control for an unknown spatial field or every possible dependence structure.
**Neither BH nor BY fixes the failed bootstrap calibration.**

The prospective primary regional family is the twelve strict variable-region
annual analyses. The Standard 100% Sahel comparison is a separate policy
sensitivity, not an extra independent replication. A future cell family would
be one variable-region-policy-period native grid. **Real regional multiplicity,
real-cell inference and all significance overlays remain withheld.**

![Synthetic FDR checks](../../../data/derived/science_inference/phase_4/synthetic_fdr.png)

## NASA data diagnostics and preservation

Thirty-nine regional candidate calculations (13 prepared series x three block
lengths) are retained in the JSON/notebook solely to expose sensitivity. They
are **not validated scientific evidence**. Their p-values and intervals are
labeled candidate/diagnostic and have `application_release=false`. A very small
candidate p-value, even 0.0005, is not sufficient after the method's null
calibration fails. No significant/inconclusive map classification is issued.

Standard 95% is explicitly withheld. Its source values, monthly support and
5,157 incomplete cell-years are not changed; no missing annual value is promoted
to a complete observation. Strict 100% and Standard 100% inputs, fixed supports,
units and Phase 3 descriptive slopes stay separate and unchanged. The twenty-
year admission guard does not establish scientific adequacy of a short record.

The study verifies 98 original hashes before and after; it writes no source
cube, original preparation, historical report or earlier notebook. The Phase 4
configuration and diagnostics are separate artifacts. Bootstrap and Monte Carlo
samples are clearly synthetic and never inserted into the delivered data.

## Acceptance and next decision

| Phase 4 validation group | Outcome |
| --- | --- |
| Versioned candidate, explicit basis, minimum guard and missing-data behavior | Implemented; software checks pass, scientific adequacy not assumed |
| Correlated-null calibration | FAIL: inflated false positives, including independent 24-year records |
| Interval coverage | FAIL: substantial undercoverage versus nominal 95% |
| Power and seasonal/missingness checks | Experiments completed; power is uncalibrated and missing records remain unsupported |
| Block and record-length sensitivity | Completed; no demonstrated repair of primary calibration |
| Trusted FDR comparison and valid-p dependency simulations | PASS for arithmetic/tested synthetic conditions; cannot repair invalid marginal p-values |
| Reviewed method/inference release | HELD: no validated candidate or Phase 5 authorization |

Recommend **rejecting this candidate for release**, retaining descriptive Phase 3
outputs, and continuing Phase 4 research. Next candidates should be specified
before evaluation and tested on independent simulations: for example, compare a
season-preserving monthly approach or an explicitly modeled dependence method,
with honest assumptions, record-length sensitivity and held-out calibration.
Include minimum-length n=20 if that admission rule is retained. Do not choose a
method by favorable NASA p-values, force a confidence interval to exclude zero,
or change alpha/coverage targets after seeing results. The need for a new
candidate is not permission to publish the failed one.

No validated inference configuration is frozen. Phase 4's scientific release
criteria remain unmet; this is a completed **research checkpoint**, not a claim
that Phase 4 is approved or that Phase 5 should start.

## Reproducibility and artifacts

```powershell
.\.venv\Scripts\python.exe tools/run_science_inference_study.py
.\.venv\Scripts\python.exe tools/validate_inference_study.py
.\.venv\Scripts\python.exe tools/run_science_inference_notebook.py
```

The full simulation run took about 6.0 minutes locally; this is a measured run,
not a service latency promise. Versions: NumPy 2.5.4,
SciPy 1.18.0, xarray 2026.9.0.

- [Study evidence](PHASE_4_STUDY.json): all 48 scenario summaries, Monte Carlo
  uncertainty, candidate gate checks, synthetic FDR results, quarantined NASA
  diagnostics, software/code/config hashes and preserved-input hashes.
- [Software/reference validation](PHASE_4_VALIDATION.json): 85 tests passed,
  no failures/skips, classical benchmark and independent accounting checks.
- [Executed notebook](../notebooks/04_inference_validation.ipynb): calibration
  tables/figures, supported/unsupported inputs, reference checks and diagnostics.
- `src/inference.py` and `config/inference_policy.json`: experimental library
  and fixed study specification. Neither is wired into an application/API.
- `data/derived/science_inference/phase_4/`: protocol, progress evidence and two
  figures, ignored by Git. The earlier immutable Phase 3 snapshot tree is untouched.

The public PR carries the research findings and limitations for review. The
preparation default, prior descriptive results and inference-release flags stay
unchanged.

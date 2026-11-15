# Phase 4: short-record dependence-uncertainty research

15 November 2026, Africa/Cairo. **Progress, but no candidate passes every screen.
Inference remains disabled; Phase 5 has not started.**

## Outcome

Accounting for dependence-parameter uncertainty improves calibration considerably.
At 24 years and true AR coefficient .7, refitted parametric bootstrap-t gives
5.5% false positives and 94.1% coverage, compared with the previous feasible
regression's 19.0% and 81.0%. These are different independent validation runs,
not a paired estimate of the improvement. At 20 years the new method still gives
10.4% false positives and 88.8% coverage in that case. It cannot be released.

A separately specified double-bootstrap experiment uses another fresh validation
stream. Strong-dependence cases give 6.5-7.3% false positives and 92.4-93.5%
coverage. This approaches the nominal targets but fails the prespecified bounds.
Neither favorable individual scenarios nor NASA p-values determine selection.
No NASA p-values were calculated in these studies. The earlier three failed
candidates and all previous evidence remain unchanged.

94 software tests pass, including four new tests for independent dense REML,
affine equivariance, repeated nuisance fitting, reproducibility, and rejected
missing/short/degenerate records. Software correctness does not override failed
scientific calibration. All earlier source, policies and validated Sen outputs
are preserved; study JSON records 109/110 prior file hashes respectively.

## Protocols fixed before evaluation

`config/uncertainty_research.json` fixes REML comparator and refitted parametric
bootstrap-t; `config/double_bootstrap_research.json` separately fixes the later
double-bootstrap experiment before its own pilot/validation. The latter was
motivated by the first study; the first validation is therefore development
evidence for it, not reused as its holdout. No thresholds were tuned afterward.

Both retain **alpha .05 and nominal confidence .95**. Approximate-target bands
are 3-7% false positives and 93-97% coverage, specified before each study, in
addition to the previous minimum screens: null Wilson upper bound <=8%, coverage
Wilson lower bound >=90%, alternative power Wilson lower bound >=20%, zero
numerical failures, all scenarios required. These screens are research criteria,
not proof of universal validity or automatic application-release authorization.

Each study has a 100-record pilot and 1,000 fresh validation records per scenario.
There are 36 scenarios: lengths 20/24, AR coefficients 0/.4/.7, known slopes
-.08/0/+.08, and absent/present annualized monthly seasonal cycles. Model errors
are stationary Gaussian AR(1) with marginal SD one and 200 burn-in samples.
Seasonal contributions use repeating monthly sine values and Gregorian day
weights, as in the previous studies. This is not general monthly inference.

First study seeds: 605731/806311; double-bootstrap seeds: 910341/117609.
Pilot, validation and inner/outer simulation streams are distinct. No candidate
was tuned between its pilot and its final validation. Trend signs/candidates
share noise within a stage; counts are paired scenario evaluations, not globally
independent datasets. Synthetic 20/24-year records are not new NASA observations.

## Methods and assumptions

### REML with small-sample Student t

For a stationary Gaussian AR(1) linear regression, profile out intercept, slope
and innovation scale. Minimize the restricted likelihood criterion
`(n-2)*log(SSE/(n-2)) + logdet(Cov) + logdet(X' Cov^-1 X)`.
The correlation search uses 59 fixed values from -.5 to .95, spacing .025.
Use n-2 residual degrees of freedom, rather than pretending scale is known.
The resulting ordinary t interval still plugs in fitted correlation; it does
not itself propagate all correlation-estimation uncertainty and is a comparator.

Dense covariance GLS/REML independently checks the whitening, criterion and
selected grid optimum. REML accounts for fixed-effect estimation in the variance
fit; this does not guarantee finite-sample confidence coverage.
Reference: [Harville (1977)](https://doi.org/10.1080/01621459.1977.10480998).
The slope is a linear regression coefficient, not a replacement for Phase 3's
robust Sen estimand outside the additive linear simulation model.

### Refitted parametric bootstrap-t

Generate stationary Gaussian AR(1) records at the fitted correlation and refit
correlation, regression coefficients and scale for every replicate. The pivot is
the bootstrap slope error divided by its refitted standard error. Invert its
2.5%/97.5% quantiles for an interval; use a plus-one absolute-pivot tail for p.
499 replicates per fitted-correlation value are fixed beforehand. Affine and
scale equivariance permit simulating zero-slope, unit-innovation records without
holding fitted nuisance parameters fixed during the replicate fits.

This propagates nuisance fitting through repeated samples, but the generating
correlation is still a plug-in estimate. It need not represent all uncertainty
about true dependence. At true .7, mean REML correlation is .606 at n=20 and .654
at n=24. Boundary estimates occur in about 14.2% and 12.5% of those nonseasonal
null trials, respectively. Bias, grid boundaries and conditional simulation can
all affect calibration; improvement is empirical, not a universal guarantee.

### Double refitted parametric bootstrap

The separate experiment simulates an outer sample, refits its correlation, then
evaluates its first-order p-value using simulations at that newly fitted value.
The final p-value is the plus-one outer empirical CDF of first-order p-values.
The confidence interval inverts the corresponding absolute-pivot critical value.
Inner simulation count is 1,999; outer count is 999. Refit nuisance parameters
at both levels. This calibrates a test construction; **the final rejection
threshold remains .05**, rather than lowering alpha to hide false positives.
It is an experimental prepivoting implementation, not a claimed exact procedure.
Discrete p/interval inversion can differ at Monte Carlo boundaries.

Both studies cache simulation distributions by n and fitted grid correlation
within each stage. Caches and records are independently generated, and caches
are separate between pilot/final stages. They are shared across final records at
the same fitted correlation: the Wilson ranges in JSON are **conditional on
these caches** and omit variation from rerunning the finite calibration cache.
Before any release, repeat complete independent cache realizations, examine
finer/wider correlation grids, and test model misspecification. This caveat is
not concealed by having 1,000 validation records. No overall unconditional
calibration guarantee is asserted.

## Comparison and release decision

The tables below show final nonseasonal nulls. Full pilot/final results, Wilson
ranges, power, seasonal patterns, boundary rates and interval widths are in
[REML evidence](PHASE_4_REML_RESEARCH.json) and
[double-bootstrap evidence](PHASE_4_DOUBLE_BOOTSTRAP.json).

The REML t comparator fails 24/36 final scenario screens; refitted bootstrap-t
fails 18/36; the double bootstrap fails 16/36 on its own fresh stream. Power
failures count too; null-rate and coverage failures alone already prevent release.
Do not pool the distinct seeds as one paired candidate ranking or choose a
method by a favorable realization. Final widths and computational costs also
matter; conservatively huge intervals are not automatically the requested
approximately nominal calibration.

The project is not failing: these experiments isolate meaningful improvements
while detecting remaining short-record limitations before publishing conclusions.
Keep the descriptive outputs and strict default, retain Standard 95% as
experimental, and **continue Phase 4 research**. Neither new candidate nor the
older failed candidates should supply scientific p-values, released intervals,
real-cell significance classifications or Phase 5 outputs yet.

No source data are imputed or modified. Bootstrap simulations are explicitly
synthetic and never inserted into NASA observations. No nuisance parameter is
chosen using favorable NASA evidence. All candidate release flags remain false.

## Reproduction

```powershell
.\.venv\Scripts\python.exe tools/research_reml_uncertainty.py
.\.venv\Scripts\python.exe tools/research_double_bootstrap.py
.\.venv\Scripts\python.exe -m unittest discover -s packages/science/tests -q
```

Protocol files with before-evaluation hashes are in ignored
`data/derived/science_inference/reml_research/` and `double_bootstrap/`.
Implementation: `src/reml_uncertainty.py`, with dense-reference tests in
`tests/test_reml_uncertainty.py`. Prior bootstrap/MK/feasible-regression code and
validated Sen estimates are unchanged. Computational caching makes these runs
fast; it does not eliminate Monte Carlo calibration error or the assumptions above.

## Final nonseasonal null comparisons

| Method | Years | True rho | False positives | Coverage | Screen |
| --- | --- | --- | --- | --- | --- |
| reml_small_sample_t | 20 | 0.0 | 5.2% | 94.8% | True |
| reml_refitted_parametric_bootstrap_t | 20 | 0.0 | 4.4% | 95.3% | True |
| reml_small_sample_t | 20 | 0.4 | 9.5% | 90.5% | False |
| reml_refitted_parametric_bootstrap_t | 20 | 0.4 | 6.9% | 92.9% | False |
| reml_small_sample_t | 20 | 0.7 | 16.1% | 83.9% | False |
| reml_refitted_parametric_bootstrap_t | 20 | 0.7 | 10.4% | 88.8% | False |
| reml_small_sample_t | 24 | 0.0 | 5.7% | 94.3% | True |
| reml_refitted_parametric_bootstrap_t | 24 | 0.0 | 4.7% | 94.8% | True |
| reml_small_sample_t | 24 | 0.4 | 9.2% | 90.8% | False |
| reml_refitted_parametric_bootstrap_t | 24 | 0.4 | 6.2% | 93.3% | True |
| reml_small_sample_t | 24 | 0.7 | 8.7% | 91.3% | False |
| reml_refitted_parametric_bootstrap_t | 24 | 0.7 | 5.5% | 94.1% | True |
| double_refitted_parametric | 20 | 0.0 | 5.8% | 94.2% | True |
| double_refitted_parametric | 20 | 0.4 | 5.4% | 94.6% | True |
| double_refitted_parametric | 20 | 0.7 | 6.9% | 93.1% | False |
| double_refitted_parametric | 24 | 0.0 | 4.8% | 95.2% | True |
| double_refitted_parametric | 24 | 0.4 | 5.4% | 94.6% | True |
| double_refitted_parametric | 24 | 0.7 | 7.3% | 92.4% | False |

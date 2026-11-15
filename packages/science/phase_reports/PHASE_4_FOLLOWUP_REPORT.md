# Phase 4 follow-up: candidate comparison and bootstrap diagnosis

15 November 2026, Africa/Cairo. Research checkpoint complete.
**Both candidates fail scientific validation. Inference remains disabled.
Phase 5 has not started.**

## Prespecified acceptance and independent validation

Before evaluation, `config/inference_followup.json` was saved with code/config
hashes in `data/derived/science_inference/followup/protocol_before_evaluation.json`.
Every scenario must have false-positive Wilson upper bound <=8%, coverage Wilson
lower bound >=90%, alternative-power Wilson lower bound >=20%, and zero failed
fits. Nominal targets remain 5% and 95%; these minimum research screens alone
would not authorize release. No threshold or method was tuned after the pilot.

Pilot: 200 trials per scenario, seed 731155. Final: 1,000 fresh trials per
scenario, seed 9906115. Lengths 20/24, AR coefficients 0/.4/.7, known slopes
-.08/0/+.08 and absent/present seasonal profiles give 36 scenarios per method.
Candidates share records; trend signs share noise within each stage. There are
36,000 holdout input evaluations, not 72,000 independent datasets. Each rate uses
its own independent within-scenario trials. Pilot/final/diagnosis streams differ.

Seasonal scenarios add a repeating monthly sine cycle of amplitude three to
annual AR errors spread over constituent months, then use actual Gregorian day
weights. This tests annual preparation with seasonal patterns, not arbitrary
monthly inference. Errors are stationary Gaussian AR(1), marginal SD one, with
200 burn-in samples. Simulations are not new NASA observations or forecasts.

## Candidate assumptions

**Adjusted MK:** tie-corrected S variance, Sen-detrended residual ranks,
significant ACF lags through floor(n/4), threshold 1.96/sqrt(n), variance factor
floored at one, continuity-corrected normal tail. Its experimental Sen interval
uses adjusted-variance pair-slope order-statistic inversion. This is a stated
Hamed-Rao-style variant, not bit-for-bit equivalence to every implementation;
lag truncation, variance floor and interval construction are candidate choices.
The interval fails empirical coverage. Short-record rank-dependence estimation
can leave inadequate variance inflation; this is a plausible contributor, not
proof that every modified MK method fails universally.
Sources: [Hamed and Rao](https://doi.org/10.1016/S0022-1694(97)00125-X),
[modifiedmk documentation](https://search.r-project.org/CRAN/refmans/modifiedmk/html/mmkh.html).

**AR(1) regression:** iterative stationary Prais-Winsten feasible GLS with an
intercept and elapsed-year slope; estimated residual rho clipped to [-.95,.95],
50 iterations, tolerance 1e-7. The first row retains stationary information via
sqrt(1-rho^2); subsequent rows use AR differences. Plug-in covariance and Student
t with n-3 degrees of freedom do not fully account for estimated-rho uncertainty.
Failed convergence counts against acceptance, not as a silently excluded fit.
Its linear conditional-mean slope differs from the Sen estimand outside the
tested additive linear model; it never replaces validated Phase 3 estimates.
Assumptions include linear mean, stationary AR(1), Gaussian homoskedastic
innovations and correct model specification.
[GLSAR documentation](https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.GLSAR.html)
provides iterative regression context; this stationary first-row implementation
is not claimed identical to GLSAR.

## Main findings

Adjusted MK fails 24 of 36 holdout screens; regression fails 29. At true rho=.7,
regression estimates average rho about .43 at n=20 and .47 at n=24. Downward
estimation and plug-in uncertainty are plausible contributors to undercoverage,
not a uniquely proven causal explanation. Dense covariance GLS independently
verifies whitening for negative/zero/positive fixed rho, max error 9.13e-16.

90 software tests pass, including five new follow-up tests for dense GLS,
invariance, tie handling, invalid inputs, and missing/short/constant admission.
Software success does not override scientific calibration failures. All 105
earlier source/policy/preparation/trend/reference/notebook hashes are unchanged.
No NASA p-values were evaluated or used for method selection in this follow-up.

## Independent-data bootstrap investigation

The original failed bootstrap and its evidence remain unchanged. A new diagnosis
uses 200 independent Gaussian null records of length 24 and 499 resamples each;
an independent 5,000-record population estimates true slope sampling SD.
Diagnostic seed 440158 and population seed 550198 differ from pilot/holdout.

True sampling SD is .030868. Mean fitted-residual IID bootstrap SD is 80.6% of
that value, with 89.5% coverage; four-year blocks give 70.1% and 81.5% coverage.
Using true null noise rather than detrended residuals still gives only 83.9%
of sampling SD for IID resampling, and 77.6% with blocks. Known-Gaussian draws
with true noise SD give 99.8% and 94.5% coverage. These oracle comparisons are
diagnostics, not deployable methods: true noise distribution/scale are unknown.

Detrending reduces sample variance to .956 of raw variance on average, too small
alone to explain the entire uncertainty deficit. IID empirical resamples contain
15.35 distinct source positions out of 24 on average, creating discrete repeats.
Finite empirical resampling, fitting constraints, few blocks and circular
boundaries can all affect the error distribution. The evidence localizes failure
to empirical/residual resampling rather than an annual unit error or failure of
affine reconstruction. It does not uniquely identify ties or detrending as the
single cause; a fuller factorial design is needed for causal attribution.
Full diagnostic intervals and measurements are in the JSON.

## Release recommendation

Reject both tested candidates for release. Preserve the descriptive results and
strict default; Standard 95% remains experimental, with missing cell-years intact.
Do not correct invalid marginal p-values with FDR or start Phase 5. No real-cell
inference, significance maps or application inference outputs were produced.
The original bootstrap remains a failed reference, not a silently repaired method.

Continue Phase 4 research on small-sample dependence-parameter uncertainty or
another prespecified method, using another untouched validation stream. Do not
choose favorable NASA p-values, change targets after seeing results, or claim
universal calibration from finite simulations. Scientific release stays false.

## Reproduction

```powershell
.\.venv\Scripts\python.exe tools/research_inference_followup.py
.\.venv\Scripts\python.exe -m unittest discover -s packages/science/tests -q
```

Sources: `src/inference_candidates.py`, `config/inference_followup.json`,
`tests/test_inference_candidates.py`. [Full evidence](PHASE_4_FOLLOWUP.json)
contains both pilot and holdout results, Wilson rate uncertainty, failure counts,
slope bias, rho estimates, diagnosis, code hashes and preservation checks.
Null rejection rates estimate false positives; alternative rejection rates are
uncalibrated power when the null gate fails. Coverage includes only valid fits;
acceptance separately requires zero failed fits. Missing and short inputs return
no interval and are not counted as successfully covered observations.

## Holdout comparison tables

| Candidate | Years | AR | Season | Truth/year | Reject rate | Coverage | Failed fits | Screen |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| adjusted_mk | 20 | 0 | none | -0.08 | 0.436 | 0.963 | 0 | True |
| ar1_regression | 20 | 0 | none | -0.08 | 0.518 | 0.937 | 0 | True |
| adjusted_mk | 20 | 0 | none | 0 | 0.041 | 0.963 | 0 | True |
| ar1_regression | 20 | 0 | none | 0 | 0.063 | 0.937 | 0 | True |
| adjusted_mk | 20 | 0 | none | 0.08 | 0.435 | 0.963 | 0 | True |
| ar1_regression | 20 | 0 | none | 0.08 | 0.519 | 0.937 | 0 | True |
| adjusted_mk | 20 | 0 | monthly_cycle_annualized | -0.08 | 0.422 | 0.964 | 0 | True |
| ar1_regression | 20 | 0 | monthly_cycle_annualized | -0.08 | 0.525 | 0.932 | 0 | True |
| adjusted_mk | 20 | 0 | monthly_cycle_annualized | 0 | 0.04 | 0.964 | 0 | True |
| ar1_regression | 20 | 0 | monthly_cycle_annualized | 0 | 0.068 | 0.932 | 0 | False |
| adjusted_mk | 20 | 0 | monthly_cycle_annualized | 0.08 | 0.455 | 0.964 | 0 | True |
| ar1_regression | 20 | 0 | monthly_cycle_annualized | 0.08 | 0.553 | 0.932 | 0 | True |
| adjusted_mk | 20 | 0.4 | none | -0.08 | 0.477 | 0.856 | 0 | False |
| ar1_regression | 20 | 0.4 | none | -0.08 | 0.424 | 0.887 | 0 | False |
| adjusted_mk | 20 | 0.4 | none | 0 | 0.153 | 0.856 | 0 | False |
| ar1_regression | 20 | 0.4 | none | 0 | 0.113 | 0.887 | 0 | False |
| adjusted_mk | 20 | 0.4 | none | 0.08 | 0.455 | 0.856 | 0 | False |
| ar1_regression | 20 | 0.4 | none | 0.08 | 0.416 | 0.887 | 0 | False |
| adjusted_mk | 20 | 0.4 | monthly_cycle_annualized | -0.08 | 0.49 | 0.834 | 0 | False |
| ar1_regression | 20 | 0.4 | monthly_cycle_annualized | -0.08 | 0.415 | 0.87 | 0 | False |
| adjusted_mk | 20 | 0.4 | monthly_cycle_annualized | 0 | 0.173 | 0.834 | 0 | False |
| ar1_regression | 20 | 0.4 | monthly_cycle_annualized | 0 | 0.13 | 0.87 | 0 | False |
| adjusted_mk | 20 | 0.4 | monthly_cycle_annualized | 0.08 | 0.473 | 0.834 | 0 | False |
| ar1_regression | 20 | 0.4 | monthly_cycle_annualized | 0.08 | 0.389 | 0.87 | 0 | False |
| adjusted_mk | 20 | 0.7 | none | -0.08 | 0.476 | 0.751 | 0 | False |
| ar1_regression | 20 | 0.7 | none | -0.08 | 0.408 | 0.818 | 0 | False |
| adjusted_mk | 20 | 0.7 | none | 0 | 0.259 | 0.751 | 0 | False |
| ar1_regression | 20 | 0.7 | none | 0 | 0.182 | 0.818 | 0 | False |
| adjusted_mk | 20 | 0.7 | none | 0.08 | 0.499 | 0.751 | 0 | False |
| ar1_regression | 20 | 0.7 | none | 0.08 | 0.418 | 0.818 | 0 | False |
| adjusted_mk | 20 | 0.7 | monthly_cycle_annualized | -0.08 | 0.502 | 0.721 | 0 | False |
| ar1_regression | 20 | 0.7 | monthly_cycle_annualized | -0.08 | 0.434 | 0.784 | 0 | False |
| adjusted_mk | 20 | 0.7 | monthly_cycle_annualized | 0 | 0.284 | 0.721 | 0 | False |
| ar1_regression | 20 | 0.7 | monthly_cycle_annualized | 0 | 0.216 | 0.784 | 0 | False |
| adjusted_mk | 20 | 0.7 | monthly_cycle_annualized | 0.08 | 0.481 | 0.721 | 0 | False |
| ar1_regression | 20 | 0.7 | monthly_cycle_annualized | 0.08 | 0.437 | 0.784 | 0 | False |
| adjusted_mk | 24 | 0 | none | -0.08 | 0.667 | 0.942 | 0 | True |
| ar1_regression | 24 | 0 | none | -0.08 | 0.75 | 0.91 | 0 | False |
| adjusted_mk | 24 | 0 | none | 0 | 0.058 | 0.942 | 0 | True |
| ar1_regression | 24 | 0 | none | 0 | 0.09 | 0.91 | 0 | False |
| adjusted_mk | 24 | 0 | none | 0.08 | 0.648 | 0.942 | 0 | True |
| ar1_regression | 24 | 0 | none | 0.08 | 0.738 | 0.91 | 0 | False |
| adjusted_mk | 24 | 0 | monthly_cycle_annualized | -0.08 | 0.652 | 0.957 | 0 | True |
| ar1_regression | 24 | 0 | monthly_cycle_annualized | -0.08 | 0.741 | 0.925 | 0 | True |
| adjusted_mk | 24 | 0 | monthly_cycle_annualized | 0 | 0.04 | 0.957 | 0 | True |
| ar1_regression | 24 | 0 | monthly_cycle_annualized | 0 | 0.075 | 0.925 | 0 | False |
| adjusted_mk | 24 | 0 | monthly_cycle_annualized | 0.08 | 0.666 | 0.957 | 0 | True |
| ar1_regression | 24 | 0 | monthly_cycle_annualized | 0.08 | 0.754 | 0.925 | 0 | True |
| adjusted_mk | 24 | 0.4 | none | -0.08 | 0.624 | 0.833 | 0 | False |
| ar1_regression | 24 | 0.4 | none | -0.08 | 0.565 | 0.891 | 0 | False |
| adjusted_mk | 24 | 0.4 | none | 0 | 0.161 | 0.833 | 0 | False |
| ar1_regression | 24 | 0.4 | none | 0 | 0.109 | 0.891 | 0 | False |
| adjusted_mk | 24 | 0.4 | none | 0.08 | 0.605 | 0.833 | 0 | False |
| ar1_regression | 24 | 0.4 | none | 0.08 | 0.544 | 0.891 | 0 | False |
| adjusted_mk | 24 | 0.4 | monthly_cycle_annualized | -0.08 | 0.594 | 0.86 | 0 | False |
| ar1_regression | 24 | 0.4 | monthly_cycle_annualized | -0.08 | 0.543 | 0.887 | 0 | False |
| adjusted_mk | 24 | 0.4 | monthly_cycle_annualized | 0 | 0.136 | 0.86 | 0 | False |
| ar1_regression | 24 | 0.4 | monthly_cycle_annualized | 0 | 0.113 | 0.887 | 0 | False |
| adjusted_mk | 24 | 0.4 | monthly_cycle_annualized | 0.08 | 0.634 | 0.86 | 0 | False |
| ar1_regression | 24 | 0.4 | monthly_cycle_annualized | 0.08 | 0.569 | 0.887 | 0 | False |
| adjusted_mk | 24 | 0.7 | none | -0.08 | 0.578 | 0.725 | 0 | False |
| ar1_regression | 24 | 0.7 | none | -0.08 | 0.515 | 0.81 | 0 | False |
| adjusted_mk | 24 | 0.7 | none | 0 | 0.274 | 0.725 | 0 | False |
| ar1_regression | 24 | 0.7 | none | 0 | 0.19 | 0.81 | 0 | False |
| adjusted_mk | 24 | 0.7 | none | 0.08 | 0.561 | 0.725 | 0 | False |
| ar1_regression | 24 | 0.7 | none | 0.08 | 0.5 | 0.81 | 0 | False |
| adjusted_mk | 24 | 0.7 | monthly_cycle_annualized | -0.08 | 0.548 | 0.733 | 0 | False |
| ar1_regression | 24 | 0.7 | monthly_cycle_annualized | -0.08 | 0.504 | 0.806 | 0 | False |
| adjusted_mk | 24 | 0.7 | monthly_cycle_annualized | 0 | 0.262 | 0.733 | 0 | False |
| ar1_regression | 24 | 0.7 | monthly_cycle_annualized | 0 | 0.194 | 0.806 | 0 | False |
| adjusted_mk | 24 | 0.7 | monthly_cycle_annualized | 0.08 | 0.559 | 0.733 | 0 | False |
| ar1_regression | 24 | 0.7 | monthly_cycle_annualized | 0.08 | 0.507 | 0.806 | 0 | False |

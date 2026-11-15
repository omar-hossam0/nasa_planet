# Phase 4 checkpoint: estimand-aligned Sen inference

15 November 2026, Africa/Cairo. **Research checkpoint complete; no candidate
is suitable for release. Inference remains disabled. Phase 5 has not started.**

## Recommended direction and tested result

Recommend **Sen-centered nuisance-aware Monte Carlo test inversion** for further
research, rather than attaching regression intervals to Sen descriptions. The
point estimate in every tested candidate is exactly the Phase 3 pairwise-median
Sen estimator. None overwrites the delivered data, existing slopes or policies.

The tested full correlation-grid envelope is an informative conservative baseline,
not the final recommended production method: it overcovers and sacrifices power.
The next proposed extension would maximize over an independently validated
confidence set for the nuisance correlation, with an explicit confidence-set
error budget added to the p-value. **That confidence-set extension has not been
implemented or validated here**; narrowing a grid after seeing favorable results
would not be acceptable. The current full-grid method is not released.

Three approaches were tested with the same scientific targets:

- **Sen subsampling**, three prespecified block fractions: inadequate short-record
  coverage, including independent observations. Not recommended for these records.
- **Sen parametric plug-in:** direct simulation of the Sen pivot at fitted
  correlation. Better estimand consistency but persistent false-positive inflation.
- **Sen nuisance-grid envelope:** maximize the simulated tail over all prespecified
  correlations. Avoids choosing one favorable fitted correlation, but is far too
  conservative in the supported Gaussian scenarios, and not robust outside scope.

At true AR coefficient .7, plug-in false positives average 10.98%/11.32% at
n=20/24, with coverage 89.02%/88.68%. The grid envelope gives .58%/.60% false
positives and 99.43%/99.40% coverage. That is not approximately 5%/95% behavior;
being more conservative is not an automatic pass. The shortest subsampling
fraction gives about 30.9%/27.8% false positives in these strong-dependence cases.

## Acceptance defined before evaluation

`config/sen_uncertainty_research.json`, code hashes, input hashes and the unchanged
acceptance rules were saved before the experiment. Nominal alpha stays **.05**,
confidence **.95**. The earlier screens remain: null rate 3-7%, coverage 93-97%,
null Wilson upper bound <=8%, coverage Wilson lower bound >=90%, alternative
power Wilson lower bound >=20%, zero numerical failures, all required scenarios.
No threshold was weakened to favor a method. No NASA p-values were calculated
or used for candidate, block, cache or nuisance-range selection.

The fresh validation uses four independent cache/panel pairs, 1,000 records per
panel, lengths 20/24, slopes -.08/0/+.08 and multiple correlation strengths.
Cache seed 542801 and record seed 914073 are new, distinct from earlier studies.
Calibration simulations and validation records use separate streams. No parameter
was tuned between caches. There are 1,080 scenario/candidate/cache summaries:
1,080,000 paired record evaluations, not independent datasets. Underlying noise
panels number 72,000 records; methods, trends and blocks reuse those panels.

Each parametric cache uses 4,999 independent stationary Gaussian AR(1) replicates
per n/rho value. Four cache/panel pairs are the independent units for aggregate
Monte Carlo uncertainty; conditional Wilson ranges describe individual panels.
Cluster-t intervals with only four units are rough, not a proof of universal
calibration. They include cache and record variation without pretending that
all 4,000 records share an independently estimated calibration distribution.

## Target quantity and estimator consistency

The supported scientific target is beta in `Y(t)=a+beta*t+error(t)`, with an
additive symmetric error model and explicitly equally spaced annual coordinates.
Every point estimate is Sen; its source identity and equality to the shared
validated kernel are tested. Under this model, beta is also the population
median pair-slope target. Confidence coverage is for the unknown beta, not for
the random realized finite-sample Sen estimate. This distinction remains necessary
even when the interval is centered at Sen.

The parametric pivot is `Sen(Y) / MAD(Y - Sen(Y)*t)` under beta=0. Intercept and
positive scale cancel; adding a linear trend shifts the Sen estimate without
changing its detrended scale. Tests verify these equivariances. Missing or
degenerate records are rejected, never filled with invented values. No conversion
of old regression confidence intervals into Sen intervals is performed.

For nonlinear trends, asymmetric disturbances or contaminated observations,
a single linear beta or common pairwise-median functional needs separate definition
and validation. This work does not establish universal robust uncertainty just
because the point estimate is robust. A separate regression-based result remains
possible, but must keep its own slope, assumptions and failed-validation status;
the earlier regression candidates have not been approved by this experiment.

## Candidate definitions

### Overlapping-block subsampling

Recompute Sen on each contiguous block of length floor(f*n), f=.35/.50/.65.
Center block slopes at the full Sen estimate and scale errors by `(b/n)^1.5`,
the fixed-year linear-trend rate rather than a sample-mean sqrt(n) rate. Use
the 95th percentile of absolute scaled block errors for a symmetric interval.
The p-value is the empirical fraction of block errors at least as large as the
observed absolute slope. Blocks overlap and are not exchangeable independent
Monte Carlo draws: no exact plus-one test guarantee is claimed. An empirical
tail of zero is not a claim of zero null probability.

The fixed block fractions do not satisfy the classical asymptotic regime
b/n tending to zero. With 20-24 observations there are very few distinct blocks,
and centering at the full estimator further constrains the empirical spread.
The candidate is intentionally tested rather than assumed valid from asymptotics.
The [subsampling literature](https://www3.stat.sinica.edu.tw/statistica/oldpdf/A11n49.pdf)
motivates dependent-data subsampling, not validation of these finite choices.
None of the three fractions passes the complete study; no favorable block is selected.

### Fitted-correlation parametric Sen simulation

Estimate correlation using the previously tested REML fit, then select the nearest
prespecified calibration rho. Simulations use Sen/MAD, not a regression pivot.
The point-estimate change fixes the mismatch, but a single fitted generating rho
still understates nuisance uncertainty in short records. No claim of complete
uncertainty propagation is made. Simulation at known parameter values is not
equivalent to knowing those parameters in NASA data.

### Nuisance-grid envelope

Simulate the absolute Sen/MAD pivot for rho=-.5,-.4,...,.9. For a tested beta,
take the maximum plus-one tail p-value over this fixed grid; intervals use the
largest simulated 95th percentile, centered at Sen with the observed MAD scale.
The construction avoids selecting the correlation yielding the smallest p-value.

If a true Gaussian correlation is exactly one of the grid points, the grid maximum
dominates the corresponding simple-null Monte Carlo p-value. This explains its
conservatism under those assumptions. A finite grid is **not** a maximization over
a continuous nuisance space, and no exact guarantee between points, beyond .9,
or under model misspecification is claimed. Off-grid .55 is tested explicitly.
Finite-quantile and discrete p-value endpoint conventions can differ slightly.
The [maximized Monte Carlo literature](https://jeanmariedufour.research.mcgill.ca/Dufour_2006_JE_MCT.pdf)
provides the nuisance-maximization principle, not proof for this restricted grid.

## Independent validation and misspecification

Core nulls have Gaussian AR(1) errors with rho=0/.4/.7. Additional tests use
off-grid .55, annualized repeating monthly cycles, standardized t5 innovations,
ARMA(1,1) with AR .7/MA .4, innovation scales rising from one to two, and a
boundary rho=.95 beyond the calibration grid. Annual errors use 300 burn-in
observations. ARMA's lag-one correlation is not its AR parameter .7. Seasonal
results concern annual preparation, not general monthly inference. None of
these records is a NASA observation or forecast.

The plug-in Sen test is close to nominal with independent errors, but fails the
strong-dependence cases. The envelope has zero observed false positives in
some independent-error panels, not a proven zero true rate. Under boundary .95,
even the envelope gives roughly 9.1%/8.6% false positives and 90.9%/91.4% coverage
at n=20/24. Thus a safe-looking grid result is not permission to extrapolate.
ARMA and heteroskedastic tests also challenge the Gaussian AR(1) specification.
Known increasing/decreasing alternatives are included in the full evidence;
coverage and power are never inferred from null rates alone.

## Release recommendation and next research

**No significance or uncertainty release; no significance-dependent Phase 5.**
The recommended research route is a Sen-centered nuisance-aware Monte Carlo
test/interval, with the tested envelope as a conservative reference and the
plug-in method as a failed comparison. It directly addresses the intended trend
quantity, unlike borrowing an interval from a different point estimator.

To improve efficiency without choosing a favorable rho, investigate a confidence-
set maximization with a stated nuisance-set error budget. The Berger-Boos idea
adds that error budget to a maximized p-value, rather than relaxing the final
5% threshold. See the [original paper](https://doi.org/10.1080/01621459.1994.10476836).
Such an extension requires valid small-sample nuisance confidence sets, continuous-
range or verified-grid control, independent calibration/holdout streams, and the
same misspecification tests. It is a proposal, not an already validated method.

Do not adopt the overly wide envelope as a nominally calibrated production result,
restrict the model domain after seeing results, or choose whichever method makes
NASA trends most significant. The project has gained a coherent estimand and
clearer dependence/efficiency diagnostics; its scientific release gate remains open.

## Evidence, tests and reproduction

[Evidence](PHASE_4_SEN_RESEARCH.json) records all conditions, four-cache aggregates,
conditional Wilson ranges, cluster Monte Carlo intervals, widths, bias, source
and protocol hashes. [Validation](PHASE_4_SEN_TESTS.json) records **103 passing
software tests**, including four new Sen-point equality, affine-invariance,
envelope dominance and rejected missing/degenerate-input checks. All 118 protected
previous files are unchanged; original NASA data, policies, Sen outputs and failed
reference methods remain intact. Software success does not certify calibration.

```powershell
.\.venv\Scripts\python.exe tools/research_sen_uncertainty.py
.\.venv\Scripts\python.exe tools/validate_sen_research.py
```

The source is `src/sen_uncertainty.py`; protocol and derived caches are under
ignored `data/derived/science_inference/sen_research/`. No application consumes
these candidate results. Alpha, confidence and acceptance rules are unchanged.

## Final null comparisons (four independent cache/panel means)

| Years | Method | Model | Mean false positives | Mean coverage | Failed caches / 4 |
| --- | --- | --- | --- | --- | --- |
| 20 | sen_nuisance_grid_envelope | gaussian0 | 0.00% | 100.00% | 4 |
| 20 | sen_nuisance_grid_envelope | gaussian4 | 0.07% | 99.93% | 4 |
| 20 | sen_nuisance_grid_envelope | gaussian7 | 0.58% | 99.43% | 4 |
| 20 | sen_nuisance_grid_envelope | offgrid55 | 0.18% | 99.83% | 4 |
| 20 | sen_nuisance_grid_envelope | seasonal | 0.38% | 99.63% | 4 |
| 20 | sen_nuisance_grid_envelope | student5 | 0.83% | 99.17% | 4 |
| 20 | sen_nuisance_grid_envelope | arma11 | 1.27% | 98.72% | 4 |
| 20 | sen_nuisance_grid_envelope | heteroskedastic | 0.47% | 99.52% | 4 |
| 20 | sen_nuisance_grid_envelope | boundary95 | 9.13% | 90.88% | 4 |
| 20 | sen_parametric_plugin | gaussian0 | 5.42% | 94.57% | 0 |
| 20 | sen_parametric_plugin | gaussian4 | 8.30% | 91.70% | 4 |
| 20 | sen_parametric_plugin | gaussian7 | 10.97% | 89.03% | 4 |
| 20 | sen_parametric_plugin | offgrid55 | 9.95% | 90.05% | 4 |
| 20 | sen_parametric_plugin | seasonal | 11.28% | 88.72% | 4 |
| 20 | sen_parametric_plugin | student5 | 11.90% | 88.10% | 4 |
| 20 | sen_parametric_plugin | arma11 | 7.08% | 92.92% | 4 |
| 20 | sen_parametric_plugin | heteroskedastic | 11.95% | 88.05% | 4 |
| 20 | sen_parametric_plugin | boundary95 | 22.60% | 77.40% | 4 |
| 20 | sen_subsampling_0.35 | gaussian0 | 8.80% | 91.20% | 4 |
| 20 | sen_subsampling_0.35 | gaussian4 | 16.60% | 83.40% | 4 |
| 20 | sen_subsampling_0.35 | gaussian7 | 30.90% | 69.10% | 4 |
| 20 | sen_subsampling_0.35 | offgrid55 | 23.60% | 76.40% | 4 |
| 20 | sen_subsampling_0.35 | seasonal | 29.93% | 70.08% | 4 |
| 20 | sen_subsampling_0.35 | student5 | 30.95% | 69.05% | 4 |
| 20 | sen_subsampling_0.35 | arma11 | 34.12% | 65.88% | 4 |
| 20 | sen_subsampling_0.35 | heteroskedastic | 29.65% | 70.35% | 4 |
| 20 | sen_subsampling_0.35 | boundary95 | 56.90% | 43.10% | 4 |
| 20 | sen_subsampling_0.5 | gaussian0 | 14.43% | 85.58% | 4 |
| 20 | sen_subsampling_0.5 | gaussian4 | 21.65% | 78.35% | 4 |
| 20 | sen_subsampling_0.5 | gaussian7 | 33.80% | 66.20% | 4 |
| 20 | sen_subsampling_0.5 | offgrid55 | 28.50% | 71.50% | 4 |
| 20 | sen_subsampling_0.5 | seasonal | 33.80% | 66.20% | 4 |
| 20 | sen_subsampling_0.5 | student5 | 34.38% | 65.62% | 4 |
| 20 | sen_subsampling_0.5 | arma11 | 36.48% | 63.52% | 4 |
| 20 | sen_subsampling_0.5 | heteroskedastic | 32.95% | 67.05% | 4 |
| 20 | sen_subsampling_0.5 | boundary95 | 57.55% | 42.45% | 4 |
| 20 | sen_subsampling_0.65 | gaussian0 | 21.43% | 78.57% | 4 |
| 20 | sen_subsampling_0.65 | gaussian4 | 29.88% | 70.12% | 4 |
| 20 | sen_subsampling_0.65 | gaussian7 | 41.65% | 58.35% | 4 |
| 20 | sen_subsampling_0.65 | offgrid55 | 35.60% | 64.40% | 4 |
| 20 | sen_subsampling_0.65 | seasonal | 40.83% | 59.17% | 4 |
| 20 | sen_subsampling_0.65 | student5 | 41.02% | 58.98% | 4 |
| 20 | sen_subsampling_0.65 | arma11 | 44.05% | 55.95% | 4 |
| 20 | sen_subsampling_0.65 | heteroskedastic | 41.10% | 58.90% | 4 |
| 20 | sen_subsampling_0.65 | boundary95 | 61.42% | 38.58% | 4 |
| 24 | sen_nuisance_grid_envelope | gaussian0 | 0.00% | 100.00% | 4 |
| 24 | sen_nuisance_grid_envelope | gaussian4 | 0.00% | 100.00% | 4 |
| 24 | sen_nuisance_grid_envelope | gaussian7 | 0.60% | 99.40% | 4 |
| 24 | sen_nuisance_grid_envelope | offgrid55 | 0.05% | 99.95% | 4 |
| 24 | sen_nuisance_grid_envelope | seasonal | 0.53% | 99.48% | 4 |
| 24 | sen_nuisance_grid_envelope | student5 | 0.50% | 99.50% | 4 |
| 24 | sen_nuisance_grid_envelope | arma11 | 0.97% | 99.02% | 4 |
| 24 | sen_nuisance_grid_envelope | heteroskedastic | 0.35% | 99.65% | 4 |
| 24 | sen_nuisance_grid_envelope | boundary95 | 8.60% | 91.40% | 4 |
| 24 | sen_parametric_plugin | gaussian0 | 5.72% | 94.27% | 1 |
| 24 | sen_parametric_plugin | gaussian4 | 7.65% | 92.35% | 4 |
| 24 | sen_parametric_plugin | gaussian7 | 11.32% | 88.67% | 4 |
| 24 | sen_parametric_plugin | offgrid55 | 8.88% | 91.13% | 4 |
| 24 | sen_parametric_plugin | seasonal | 10.80% | 89.20% | 4 |
| 24 | sen_parametric_plugin | student5 | 11.20% | 88.80% | 4 |
| 24 | sen_parametric_plugin | arma11 | 5.33% | 94.67% | 0 |
| 24 | sen_parametric_plugin | heteroskedastic | 11.43% | 88.58% | 4 |
| 24 | sen_parametric_plugin | boundary95 | 21.62% | 78.38% | 4 |
| 24 | sen_subsampling_0.35 | gaussian0 | 8.22% | 91.77% | 4 |
| 24 | sen_subsampling_0.35 | gaussian4 | 15.88% | 84.12% | 4 |
| 24 | sen_subsampling_0.35 | gaussian7 | 27.80% | 72.20% | 4 |
| 24 | sen_subsampling_0.35 | offgrid55 | 19.57% | 80.42% | 4 |
| 24 | sen_subsampling_0.35 | seasonal | 27.40% | 72.60% | 4 |
| 24 | sen_subsampling_0.35 | student5 | 28.27% | 71.72% | 4 |
| 24 | sen_subsampling_0.35 | arma11 | 29.90% | 70.10% | 4 |
| 24 | sen_subsampling_0.35 | heteroskedastic | 25.52% | 74.48% | 4 |
| 24 | sen_subsampling_0.35 | boundary95 | 54.97% | 45.02% | 4 |
| 24 | sen_subsampling_0.5 | gaussian0 | 14.00% | 86.00% | 4 |
| 24 | sen_subsampling_0.5 | gaussian4 | 21.55% | 78.45% | 4 |
| 24 | sen_subsampling_0.5 | gaussian7 | 31.67% | 68.33% | 4 |
| 24 | sen_subsampling_0.5 | offgrid55 | 24.62% | 75.37% | 4 |
| 24 | sen_subsampling_0.5 | seasonal | 32.03% | 67.97% | 4 |
| 24 | sen_subsampling_0.5 | student5 | 31.55% | 68.45% | 4 |
| 24 | sen_subsampling_0.5 | arma11 | 32.73% | 67.27% | 4 |
| 24 | sen_subsampling_0.5 | heteroskedastic | 29.90% | 70.10% | 4 |
| 24 | sen_subsampling_0.5 | boundary95 | 55.25% | 44.75% | 4 |
| 24 | sen_subsampling_0.65 | gaussian0 | 20.05% | 79.95% | 4 |
| 24 | sen_subsampling_0.65 | gaussian4 | 27.62% | 72.38% | 4 |
| 24 | sen_subsampling_0.65 | gaussian7 | 37.92% | 62.08% | 4 |
| 24 | sen_subsampling_0.65 | offgrid55 | 30.97% | 69.03% | 4 |
| 24 | sen_subsampling_0.65 | seasonal | 38.00% | 62.00% | 4 |
| 24 | sen_subsampling_0.65 | student5 | 36.75% | 63.25% | 4 |
| 24 | sen_subsampling_0.65 | arma11 | 38.62% | 61.38% | 4 |
| 24 | sen_subsampling_0.65 | heteroskedastic | 36.52% | 63.47% | 4 |
| 24 | sen_subsampling_0.65 | boundary95 | 58.57% | 41.42% | 4 |

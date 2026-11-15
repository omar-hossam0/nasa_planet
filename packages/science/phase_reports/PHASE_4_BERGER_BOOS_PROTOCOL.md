# Phase 4 focused experiment: Sen-centered Berger--Boos protocol

Defined before numerical evaluation, 15 November 2026. This local protocol and
its SHA-256 are recorded by the runner before any calibration or validation
draws. This is not a claim of external preregistration. One fixed candidate;
no gamma/grid/cache selection after viewing results. No NASA inference runs.

The estimand is beta in `Y_t = a + beta*t + e_t`, annual `t=0,...,n-1`.
The point estimator is the existing exact Theil--Sen kernel. Intervals target
the fixed model beta, not the realized random sample Sen estimate. Complete
20-/24-year consecutive records only; missing/degenerate inputs are rejected.
This experiment does not repair missing cell-years, alter spatial support or
generalize to raw monthly seasonal inference.

## Correlation confidence set and fixed error budget

Assume stationary Gaussian AR(1) innovations with unknown positive scale. The
candidate correlations are the **same finite grid** as the earlier Sen study:
`-.5,-.4,...,.9`. No continuous-correlation guarantee is claimed.

For each grid rho, profile out intercept, linear trend and innovation variance
using the Gaussian restricted-likelihood score
`Q_r = (n-2)*log(SSE_r/(n-2)) - log(1-r*r) + logdet(X'P_r X)`.
Here `P_r` is stationary innovation precision, `X=[1,t]`. The score difference
`D_r = Q_r - min_s Q_s` is invariant to intercept, linear slope and positive
innovation scale. Calibrate D_r separately at each generating rho, with the
entire grid refitted in every simulated record. No chi-square approximation.

Using 9,999 independent draws, the conservative upper-tail p-value is
`(1 + number of simulated D_r >= observed D_r)/10000`. Keep every rho with
`p_r > gamma`; retain disconnected components. Gamma is fixed at **.005**,
giving a nominal **99.5% correlation confidence set** under the finite-grid
Gaussian model, averaged over Monte Carlo calibration randomness. An empty
set conservatively falls back to the full grid and is counted; it is never
evidence against the trend null. Exact arithmetic normally retains a minimizer.

The trend pivot at tested beta0 is
`abs((Sen(Y)-beta0) / MAD(Y - Sen(Y)*t))`. At each rho its distribution is
simulated independently of correlation-set calibration. Define
`p_BB = min(1, max_{rho in C} p_r(beta0) + .005)` and reject at **.05**.
Thus **.005 + .045 = .05**, not a changed significance threshold. Invert the
plus-one rank rule exactly at .045: the interval is centered at Sen and uses
the largest selected critical pivot times the observed detrended MAD.

Conditional on the true rho belonging to C, maximization includes its simple
null p-value. A union bound gives at most .005 nuisance-exclusion error plus
.045 simple-null rejection error. This argument needs no independence between
the observed confidence set and trend statistic; their dependence is retained.
The simulations for their calibrations use different streams. Finite-grid
exchangeability gives an unconditional Monte Carlo bound at grid truths, not a
guarantee conditional on one reused cache, between grid points, or under a
different noise model. No additional grid-approximation budget is invented.

## Acceptance, independence and comparison

Unchanged scientific screens from `config/double_bootstrap_research.json`:
null rejection 3--7%; slope interval coverage 93--97%; null Wilson upper <=8%;
coverage Wilson lower >=90%; alternative power Wilson lower >=20%; zero
numerical failures. Every required scenario/cache must pass. Upper coverage
and lower false-positive limits remain: excessive conservatism is a failure
of the practical 5%/95% target, even when type-I control is safe under a model.

Additionally inspect correlation-set exclusion against .5% nominal. Prespecified
Monte Carlo diagnostic screens: each exact-grid Gaussian panel exclusion <=1%,
its Wilson upper <=1.5%, and aggregate mean exclusion <=.75%. These tolerances
do not replace gamma in the error budget. Record every confidence-set member,
size, endpoints, boundary inclusion, disconnected set and fallback frequency.

Four independent calibration-cache realizations; each independently generates
9,999 records per n/rho for the correlation-set statistic and another 9,999 for
the Sen pivot. Fresh validation uses 2,000 independent noise records per
n/model/cache. Seeds 602917 (calibration) and 1834901 (validation), separated
further by explicit stream/n/cache/rho/model indices; no pilot used for tuning.
See the JSON configuration for the exact fixed scenarios.

Core Gaussian correlations: -.4, 0, .4, .7, .9, each at 20/24 years. Stresses:
off-grid .55, outside-grid .95, annualized monthly cycles, standardized t5
innovations, ARMA(1,1) AR .7/MA .4, and increasing innovation scale (1 to 2).
All test slopes -.08/0/+.08 in synthetic units/year. Marginal Gaussian noise
SD is one; results are not NASA-unit detection thresholds. Trends reuse the
same noise by tested affine equivariance. Methods share panels and Sen-pivot
caches for paired comparisons; these are not independent method evaluations.

Run the unchanged existing plug-in and full-grid implementations on these fresh
panels, with the same Sen calibrations. Their historical reports stay frozen;
their old quantile endpoint convention is retained and any p/CI disagreement
is recorded. No method-specific calibration tuning or significance threshold.

Report conditional per-cache Wilson intervals and aggregate cache/panel means,
ranges and cluster-t Monte Carlo intervals with only four independent units.
These summarize simulation uncertainty, not uncertainty on NASA slopes. No
pooling that pretends shared-cache outcomes are fully independent.

## Bounded decision

Passing software tests is not scientific release. Any calibration, practical
power or supported-model failure leaves inference disabled. A misspecification
failure precludes broad NASA application claims. If this focused candidate
fails, recommend practical **descriptive-only** use of existing Phase 3 outputs,
with units, periods, policy/coverage sensitivities and no confidence or significance
claims. Do not continue unrestricted method searches. Preserve source data,
all prior results and preparation defaults. No Phase 5 work or significance
enablement is authorized by this experiment, even if the screens pass.

## Scientific references

The confidence-set maximum plus error-budget construction follows
[Berger and Boos (1994)](https://doi.org/10.1080/01621459.1994.10476836).
Finite-sample simulation with nuisance maximization and limitations of plug-in
calibration are discussed by [Dufour (2006)](https://jeanmariedufour.research.mcgill.ca/Dufour_2006_JE_MCT.pdf).
The particular Sen/MAD pivot and profile-score confidence set specified here
are this project's candidate, not a claim that those papers validate it.

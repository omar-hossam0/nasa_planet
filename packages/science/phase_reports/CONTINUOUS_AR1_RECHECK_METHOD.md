# Bounded continuous-AR1 recheck: method and limits

15 November 2026. User authorized repairing/rechecking inference and manufacturing
known-p reference data. This is a new bounded experiment, not a reclassification
of earlier failed research. Application inference remains disabled.

Implementation: `src/gaussian_ar1_inference.py`. Reproduction and retained data:
`tools/synthetic_inference_recheck_20261115/` from repository root. User-facing
report: `REPORT.md` there. Existing source data, Sen implementation, candidate
implementations and historical results are unchanged.

## Model and estimand

Y = a + beta*x + e, complete equally spaced actual annual years, stationary
Gaussian AR1 errors, covariance sigma² R(rho) with R_ij=rho^|i-j|. Sigma unknown,
intercept unknown, deterministic years. Target is the linear mean coefficient
beta, not a sampling interval for the realized median of pair slopes.

Known-rho inference must use rho fixed independently of the record. Whitening
the stationary first observation by sqrt(1-rho²) and subsequent innovations by
y[t]-rho*y[t-1] yields the ordinary Gaussian linear model. The fitted slope / SE
has a t(n-2) null distribution. SE uses residual SSE/(n-2), not n-3. Scale cancels.
Estimating rho and then treating it as known is explicitly unsupported.

Unknown rho is confined by an *external* specified range, default [-.95,.95].
No data-dependent nuisance subrange is selected. At each of 4001 equally spaced
values we evaluate the fixed-rho two-sided t p-value and interval. The reported
point estimate is OLS, explicitly labeled; the interval is an envelope of GLS
intervals. It must not be labeled a Sen interval or Mann–Kendall p-value.

## Continuous nuisance correction

For true correlation r and nearest grid correlation s, the KL divergence of
Gaussian distributions with the same mean and same marginal variance is

    K(r||s) = (n-1)/2 * [2s(s-r)/(1-s²) + log(1-s²) - log(1-r²)].

This follows by inserting the tridiagonal AR1 precision and determinant
(1-r²)^(n-1) in the multivariate normal KL formula. For fixed s the expression
is convex in r. Thus the largest divergence within each nearest-grid cell
occurs at one of its endpoints. The code evaluates all such endpoints.
Pinsker gives total variation <= epsilon=sqrt(max K/2). The implementation adds
1e-10 numeric slack; this is ordinary float64 arithmetic, not interval arithmetic
or a machine-verified proof. At n=24 and the default grid, epsilon~0.008044.

Let p_s be the exact fixed-s t p-value. Under the true r,

    P_r(p_s <= u) <= P_s(p_s <= u) + epsilon <= u + epsilon.

Since max_grid p >= p_s, min(1,max_grid p + epsilon) is a conservative p-value
under the specified model/range. For alpha=1-confidence, each grid interval
uses tail alpha-epsilon. The envelope contains the nearest-grid interval, so
noncoverage under r is bounded by alpha. Coarse grids with epsilon>=alpha are
rejected; no unbudgeted grid approximation is silently accepted.

This does NOT establish approximately 5% rejection or approximately 95%
coverage. Overcoverage/low power are visible in validation and remain failures
of the earlier practical project screens. It does not bound model
misspecification, nonstationarity, trends in variance or rho outside the range.
It is not an authorization for cell-wise or family-wise scientific claims.

## Independent numerical and simulation evidence

Ten new software tests compare against SciPy linregress and independently
constructed dense covariance/Cholesky GLS, verify an algebraically manufactured
t=3 numerical reference, compare the KL guard to dense covariance calculations,
test batching/scale/sign equivariance, and reject missing, gapped and degenerate
records. Full science suite: 128 tests + 57 subtests pass.

Nine manufactured 24-year fixtures have |t|=0,3,8 under independently fixed
rho=0,.7,.9333. Maximum p error <6.6e-13. These are algebraic reference examples,
not random calibration samples. No exact p is inferred merely from a known
generating slope. t=3 gives p=.0065946197107992904 (df22); t=8 gives
p=5.9032568211539105e-8. Nontrend fixtures produce p~1, not absent p.

Fresh validation: 26,000 independently generated records; 22,000 within-model,
4,000 stresses. Both methods share within-model records, giving 48,000
record-method evaluations, not 48,000 independent records. Protocol/both seeds
are written before evaluating outcomes. No candidate/grid/bound was selected
from validation results. n=24 primary, n=20/48 extra, off-grid rho=.9333, negative
and zero and positive generating slopes; 1000 primary or 500 extra per scenario.
Per-scenario Wilson uncertainty, bias, RMSE and every p/interval are retained.

Known-rho reference: null rejection 3.8–6.8%, coverage 93.2–96.3%, all 26
within-model scenarios pass recorded practical screens. Its known parameter is
available by construction and cannot be claimed available for NASA records.

Bounded-rho: no minimum-safety failures across 26 scenarios, but 23 fail one or
more historical practical criteria. n24 strong beta=.5 power ranges 25.4–100%;
beta=.08 power ranges 0–21.3%. This is not a complete scientific repair/release.
Outside-range rho=.99 has 8.3% null rejection and 91.7% coverage. Heavy-tailed,
AR2 and heteroskedastic stress screens are limited examples, not guarantees.

## Sources checked for the implementation

- SciPy [linregress](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.linregress.html)
  and [Student t](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.t.html).
- Gaussian [KL derivation](https://statproofbook.github.io/P/mvn-kl.html).
- [Stanford STATS 311 notes](https://web.stanford.edu/class/stats311/OldSyllabi/full_notes.pdf)
  for KL, total variation and Pinsker's inequality.

**Decision:** retain the repaired model-conditional library path and all fixtures;
keep application inference disabled. Do not relabel regression output in the
existing hard-coded Mann–Kendall/Sen conclusion path. No testing artifacts are
deleted without the user's explicit request.

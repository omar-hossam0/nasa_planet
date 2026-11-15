"""Render the fixed experiment's checkpoint tables and scientific figure."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT/'packages/science/phase_reports'
r = json.loads((REPORTS/'PHASE_4_BERGER_BOOS_RESEARCH.json').read_text())
tests = json.loads((REPORTS/'PHASE_4_BERGER_BOOS_TESTS.json').read_text())
METHODS = [('sen_parametric_plugin', 'Plug-in'),
           ('sen_nuisance_grid_envelope', 'Full grid'),
           ('sen_berger_boos', 'Berger--Boos')]
CORE = ['gaussian_negative4', 'gaussian0', 'gaussian4', 'gaussian7', 'grid_boundary9']


def item(n, model, method='sen_berger_boos', truth=0.):
    return next(x for x in r['aggregate'] if (x['n'], x['model'], x['method'], x['truth'])
                == (n, model, method, truth))


def pct(x):
    return f'{100*x:.2f}'


def comparison(models, methods):
    lines = ['| Years | Noise model / AR coefficient | Method | False positives % | Coverage % | Power - / + % |',
             '|---|---|---|---|---|---|']
    for n in [20, 24]:
        for model in models:
            for method, label in methods:
                a = item(n, model, method)
                minus = item(n, model, method, -.08)['rejection_rate']['mean']
                plus = item(n, model, method, .08)['rejection_rate']['mean']
                lines.append(f'| {n} | {model} ({a["phi"]:g}) | {label} | '
                    f'{pct(a["rejection_rate"]["mean"])} | {pct(a["coverage"]["mean"])} | '
                    f'{pct(minus)} / {pct(plus)} |')
    return '\n'.join(lines)


fig, axes = plt.subplots(2, 2, figsize=(11.2, 8), sharex=True, layout='constrained')
colors = ['#b44332', '#316f9c', '#336747']
for row, n in enumerate([20, 24]):
    for col, field in enumerate(['rejection_rate', 'coverage']):
        ax = axes[row, col]
        band = (3, 7) if col == 0 else (93, 97)
        ax.axhspan(*band, color='#ddd6ab', alpha=.45, label='Required point-rate band')
        ax.axhline(5 if col == 0 else 95, color='gray', linestyle=':', linewidth=1)
        for k, (method, label) in enumerate(METHODS):
            values = [item(n, model, method)[field] for model in CORE]
            means = np.array([v['mean']*100 for v in values])
            errors = np.array([[v['mean']-v['min'] for v in values],
                               [v['max']-v['mean'] for v in values]])*100
            ax.errorbar(np.arange(5)+(k-1)*.055, means, yerr=errors, label=label,
                        color=colors[k], marker=['o', 's', '^'][k], markersize=5,
                        linewidth=1.3, capsize=3)
        ax.set_title(f'{n} years: '+('null false positives' if col == 0 else 'slope interval coverage'))
        ax.set_ylim((-.8, 23) if col == 0 else (76, 100.8))
        ax.set_ylabel('Percent of records')
        ax.set_xticks(np.arange(5), ['-0.4', '0', '0.4', '0.7', '0.9'])
        ax.grid(axis='y', alpha=.2)
        if row == 1:
            ax.set_xlabel('True annual AR(1) coefficient; Gaussian model')
axes[0, 0].legend(fontsize=8, loc='upper left')
fig.suptitle('Sen-centered inference: independent 20- and 24-year validation\n'
             'Means of four independent cache/panel pairs; bars show their min/max (2,000 records each)', fontsize=12)
fig.savefig(REPORTS/'PHASE_4_BERGER_BOOS_COMPARISON.png', dpi=160)
plt.close(fig)

core_table = comparison(CORE, METHODS)
stress = [x['name'] for x in r['config']['models'] if not x['core']]
stress_table = comparison(stress, [('sen_berger_boos', 'Berger--Boos')])
set_lines = ['| Years | True Gaussian rho | Mean set size / 15 | True-rho exclusion % | Upper .9 included % |',
             '|---|---|---|---|---|']
for a in r['nuisance_aggregate']:
    if a['core']:
        set_lines.append(f'| {a["n"]} | {a["phi"]:g} | {a["mean_set_size"]["mean"]:.2f} | '
                         f'{pct(a["exclusion_rate"]["mean"])} | {pct(a["upper_boundary_inclusion"]["mean"])} |')
failure_lines = []
for method, label in METHODS:
    rows = [x for x in r['rows'] if x['method'] == method]
    core = [x for x in rows if x['core']]
    failure_lines.append(f'| {label} | {sum(not x["passes_screen"] for x in core)} / {len(core)} | '
                         f'{sum(not x["passes_screen"] for x in rows)} / {len(rows)} |')

report = '''# Phase 4 checkpoint: Sen-centered Berger--Boos confidence sets

15 November 2026. **Focused experiment complete. Candidate fails the practical
release targets. Recommend descriptive-only use; stop method experimentation
at this checkpoint. Inference remains disabled. Phase 5 has not started.**

Theil--Sen remains the primary estimator. All 3,683 protected files are unchanged,
including source data, earlier numerical outputs/caches, preparation policies,
validated slopes, prior scientific code and previous reports. No NASA p-values
were computed for this experiment. The new work is synthetic and isolated.

## What was specified before evaluation

The [fixed protocol](PHASE_4_BERGER_BOOS_PROTOCOL.md), configuration and code
identities were hashed before calibration or validation. The JSON result
contains the identities and the preservation manifest; the local pre-evaluation
record is `data/derived/science_inference/berger_boos/protocol_before_evaluation.json`.
This is local prospective specification, not external preregistration.

Target beta in `Y_t=a+beta*t+e_t` with equally spaced annual years. The point
estimate is the exact validated Sen median of pair slopes. The unknown beta
is the interval target, not the realized sample estimate. Gaussian stationary
AR(1) is the candidate model; the same finite correlation grid -.5,-.4,...,.9
is retained. A Gaussian nuisance fit does not replace the Sen trend estimate.

At each grid rho, invert a simulated profile-REML score-difference test to
construct a **99.5% correlation confidence set**. Calibrate each rho against
9,999 independent Gaussian records with the complete grid refitted. Retain
all rho values whose conservative plus-one p-value exceeds **gamma=.005**.
No asymptotic chi-square approximation, fitted-rho shortcut or filling of holes.
Empty sets would conservatively use the full grid; none occurred.

Use independent simulations for the Sen/detrended-MAD pivot at every rho.
For a tested beta0, `p_BB=min(1,max_{rho in C} p_r(beta0)+.005)`, evaluated at
**alpha=.05**. The budget is **.005 nuisance exclusion + .045 trend error = .05**.
The 95% interval exactly inverts this rank rule and is centered on Sen. No
significance threshold was relaxed. The observed set and trend statistic can
be dependent; the union-bound argument does not assume otherwise.

Under a true Gaussian rho exactly on the grid, this construction has a
finite-simulation unconditional level bound. It does **not** establish validity
conditional on a particular reused cache, for continuous rho between points,
beyond the grid, or for a misspecified error process. Theoretical type-I
control is also different from achieving the project's practical 5%/95% targets.

Unchanged acceptance screens: null rejection 3--7%; coverage 93--97%; null
Wilson upper <=8%; coverage Wilson lower >=90%; alternative power Wilson
lower >=20%; zero numerical failures; all required scenarios/cache panels.
Extra nuisance-set screens are in the protocol; they do not enlarge gamma.
No parameter, cache, grid, method or NASA region was selected after results.

## Independent validation and accounting

Four independent cache/panel pairs, lengths 20/24, eleven noise scenarios,
2,000 records per panel, and slopes -.08/0/+.08 synthetic units/year. Calibration
seed 602917 and validation seed 1834901 are distinct from earlier studies.
Correlation-set and Sen-pivot simulations have separate stream identifiers.
There are **2,399,760 calibration records**, **176,000 unique validation noise
records** and **1,584,000 paired method/trend record evaluations** (792 summaries).
Methods and trend signs share noise panels; those evaluations are not independent
datasets. All increasing/decreasing coverage and power results are retained.

Plug-in and full-grid methods use their existing unchanged implementations on
the fresh panels with the same new Sen-pivot caches. Their earlier results stay
frozen. Their historical interval quantile convention is retained; no observed
p/interval disagreement occurred in this run. The new method uses exact rank
inversion; no disagreements occurred there either.

Tables show means across four independent cache/panel pairs. Per-panel Wilson
intervals and cache/panel min/max and cluster-t Monte Carlo intervals are in
[the numerical checkpoint](PHASE_4_BERGER_BOOS_RESEARCH.json). Four clusters
give imprecise Monte Carlo uncertainty; they are not 8,000 independent cache
estimates. These ranges are simulation diagnostics, not NASA confidence intervals.

## Paired comparison under the specified Gaussian model

Power columns correspond to the known slopes **-.08 / +.08**, respectively.
Both use marginal Gaussian noise SD one; they are not physical NASA thresholds.
Coverage is the same across the three slopes by tested affine equivariance.

@CORE_TABLE@

![Fresh synthetic null calibration; error bars are cache/panel ranges](PHASE_4_BERGER_BOOS_COMPARISON.png)

At rho=.7, Berger--Boos false positives are **0.74% / 0.61%** and coverage
**99.26% / 99.39%** for 20/24 years. Positive-trend power is **2.86% / 3.74%**;
negative-trend power **2.77% / 4.03%**. Null false-positive cache/panel ranges
are .55--1.00% / .50--.70%; approximate cluster-mean Monte Carlo intervals
are .41--1.06% / .48--.75%. The practical failure is not close to a 3% lower
false-positive target or 20% lower power screen.

At the upper grid point .9, false positives (4.27% / 4.34%) and coverage
(95.72% / 95.66%) are close to target, but positive power is only 12.85% / 17.01%.
This favorable null case cannot override failures elsewhere. Independent errors
also remain too conservative: false positives .21% / .24%, coverage 99.79% /
99.76%. Negative dependence does not rescue all screens.

| Method | Failed core cache/scenario screens | Failed all cache/scenario screens |
|---|---|---|
@FAILURE_TABLE@

Every method fails release. These counts include paired slopes and reused
caches and must not be treated as independent failure probabilities.

## Did the correlation confidence set work?

Its prespecified diagnostic screens passed. Mean exclusion at exact-grid
Gaussian truths ranges from .40% to .59%, near the .5% budget. All per-cache
screens passed. This finite experiment supports the implementation under the
specified model; it does not prove general or conditional-on-cache calibration.

@SET_TABLE@

At rho=.7, the sets retain roughly **10.00 / 9.08 of 15 rho values** and include
.9 for **98.91% / 98.12%** of records. Short records with an unknown trend
provide too little information to exclude highly dependent errors at 99.5%
confidence. Maximization therefore often resembles the conservative full-grid
envelope; adding gamma can even make it slightly wider. Sometimes confidence-
set restriction improves power, especially for negative dependence, but it does
not recover the required coverage/calibration/power combination.

The evidence points to weak nuisance identification and a worst-case tail
penalty, not a demonstrated failure of the error-budget principle. We do not
try a larger gamma, narrower grid or favorable seed after seeing this outcome.
Finite grid resolution remains a separate, unresolved scientific limitation.

## Misspecification, off-grid and boundary stresses

The seasonal case adds a repeating monthly cycle after calendar-day-weighted
annual aggregation; it does not validate raw monthly inference. Student5 has
standardized t5 innovations. ARMA uses AR .7 and MA .4: .7 is **not** its lag-one
correlation. Heteroskedastic innovations grow in scale from one to two. These
tests keep the linear slope target but challenge the Gaussian AR(1) assumptions.

@STRESS_TABLE@

The off-grid .55 case remains far too conservative; it supplies no theorem for
the continuum. Heavy tails, ARMA and changing variance also fail the practical
screens. Outside-grid rho=.95 yields **7.53% / 8.81%** false positives and
**92.48% / 91.19%** coverage. Here the true rho cannot belong to the finite set,
so the finite-grid union-bound premise is absent. Narrowing a grid to improve
power cannot be treated as protection against stronger persistence.

JSON `excluded` values for non-Gaussian grid-indexable stresses describe exclusion
of the generating AR coefficient only; they are not validated nuisance coverage
for those misspecified models. Off-grid/outside-grid exclusion is null, not
an invented coverage rate. The separate range-bracketing metric is descriptive.

No results establish robustness to nonlinear trends, asymmetric errors, severe
outliers, nonstationarity, missing years, changing spatial support or multiple
cell testing. A robust descriptive estimator does not make its parametric
uncertainty method robust to every error process.

## Practical recommendation: a descriptive-only application

**Reject this candidate for release and end this sequence of method searches.**
The existing data and validated descriptive work remain useful. Recommend this
bounded application scope for owner review, without implementing Phase 5 now:

1. Use the existing Phase 3 regional Sen slopes with explicit variable units,
   units/year, dates and observed record counts. Keep raw monthly, monthly
   anomaly and complete-annual summaries separately labeled. Show observed
   series and a labeled descriptive trend summary; do not imply forecasts.
2. Keep Strict 100% as the unchanged default/control. Present Standard 100%
   separately as preparation-policy sensitivity. Label Standard 95% experimental;
   expose monthly valid-area support, preserve missing cell-years, and never
   present its incomplete cell-years as complete annual observations.
3. Carry forward provenance, QA, eligible/excluded area denominators, month/year
   completeness and changing-support warnings from existing artifacts. A
   regional slope describes the selected contributing footprint and period.
4. Offer policy and period sensitivity as **descriptive comparisons**, using
   approved existing definitions. A spread across cells, periods or policies
   is not a confidence interval and does not measure a calibrated error rate.
5. Display `Inference unavailable: short-record uncertainty validation did not
   meet release targets`. Withhold p-values, confidence bands, significant/
   non-significant labels, FDR decisions, confidence rankings and significance
   shares. Increasing/decreasing descriptive signs do not establish certainty
   or causation; a failed/inconclusive inference method does not imply stability.
6. Seek review of this descriptive-only scope before subsequent integration or
   Phase 5 work. Further method research needs a new, explicitly bounded
   scientific decision; this report does not authorize more experimentation.

This rejects the configured method for the tested product scope, not every
possible uncertainty method or the value of the data. The fixed power benchmark
is a practical requirement, not a claim that all real physical trends of that
magnitude are detectable in 20 years.

This is a product recommendation, not a completed application release. Inference
flags remain false, no scientific method is frozen as approved, and Phase 5
remains NOT_STARTED. The user's existing phase boundaries are preserved.

## Verification and reproduction

**@TEST_COUNT@ software tests pass**; seven new tests cover dense-covariance score
references, affine invariance, exact rank inversion/ties, explicit budget and
manual maximization, missing/degenerate guards and stationary AR simulation.
The saved-evidence validator recomputes all 88 new-candidate panels, checks
all 792 record-level summaries and all aggregate arithmetic, and verifies
264 independent SciPy Sen comparisons (maximum absolute slope error zero).
Zero numerical failures and zero new-candidate test/interval disagreements.
Passing these checks does not reverse the failed scientific screens.

The validator verifies 96 saved evidence files, the pre-evaluation protocol and
all 3,683 protected prior files by SHA-256. Earlier NASA data, Stage 2/3 arrays,
all previous Phase 4 results and previous code/configuration/tests are unchanged.
Only this experiment's new files and current plan/progress documentation change.

From the repository root:

```powershell
.\\.venv\\Scripts\\python.exe tools/research_berger_boos.py
.\\.venv\\Scripts\\python.exe tools/validate_berger_boos.py
.\\.venv\\Scripts\\python.exe tools/render_berger_boos_checkpoint.py
```

The runner writes new caches and record-level evidence under ignored
`data/derived/science_inference/berger_boos/`. Committed JSON retains all scenario
summaries, acceptance rules, seeds and preservation/evidence hashes. Old studies
are not rerun or overwritten. Reproduction is not a proposed new method search.

## References and prior evidence

Confidence-set maximization with an added error budget follows
[Berger and Boos (1994)](https://doi.org/10.1080/01621459.1994.10476836).
[Dufour (2006)](https://jeanmariedufour.research.mcgill.ca/Dufour_2006_JE_MCT.pdf)
discusses finite-sample Monte Carlo tests with nuisance maximization and the
limits of plug-in approaches. Neither source validates our particular Sen/MAD
pivot or grid. The union-bound application and simulation results above are
this experiment's derivation and evidence, not claims copied from those papers.

Earlier [Sen comparisons](PHASE_4_SEN_REPORT.md) and
[double-bootstrap diagnosis](PHASE_4_DOUBLE_DIAGNOSIS_REPORT.md) remain intact.
Machine-readable evidence: [research](PHASE_4_BERGER_BOOS_RESEARCH.json) and
[verification](PHASE_4_BERGER_BOOS_TESTS.json).
'''
report = (report.replace('@CORE_TABLE@', core_table).replace('@STRESS_TABLE@', stress_table)
          .replace('@SET_TABLE@', '\n'.join(set_lines)).replace('@FAILURE_TABLE@', '\n'.join(failure_lines))
          .replace('@TEST_COUNT@', str(tests['tests_run'])))
(REPORTS/'PHASE_4_BERGER_BOOS_REPORT.md').write_text(report, encoding='utf-8')
print('Checkpoint report and comparison figure written.')

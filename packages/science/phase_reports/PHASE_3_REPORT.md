# Phase 3 checkpoint: descriptive Theil-Sen trend estimation

Date: 15 November 2026. Branch: `codex/ml-statistics`.
Status: **DONE_WAITING_APPROVAL**. Stop here for review; Phase 4 is **NOT_STARTED**.

## Outcome and authorization

Stage 2 approval and the user's instruction to implement Phase 3 are recorded in
[PHASE_2_APPROVAL.md](PHASE_2_APPROVAL.md). Descriptive regional and cell-level
Theil-Sen estimation is implemented and validated. **72 tests pass**, including
21 new trend tests; **210 slope-only reference comparisons** pass, with maximum
absolute difference **5.55e-17** in the native slope units.
All **72 preserved Stage 2 source/policy/preparation/review files remain byte-identical**.
No default policy, original preparation output or earlier notebook was changed.

Fourteen cases were evaluated: the twelve strict-policy variable/region pairs,
a separate Standard 100% Sahel NDVI comparison, and an explicitly experimental
Standard 95% Sahel NDVI sensitivity. Each has regional monthly/annual results
and native-grid cell slopes. There are 62,396 computed cell slopes per temporal
basis across these cases; overlapping policy footprints are not independent
observations and this sum is not a count of unique spatial cells.

No p-values, confidence intervals, significance classes, inferential decisions,
bootstrap runs, forecasts or causal claims were generated. Method/application
readiness flags and inherited inference configuration remain unchanged.

| Phase 3 acceptance group | Status | Evidence |
| --- | --- | --- |
| Explicit monthly/annual year axes and annual-unit regression | PASS | Mandatory time coordinates, known annual +1/year result |
| Shared regional/cell estimator and minimum-guard parity | PASS | Same kernel, batch/scalar checks, shared 48/60 fixture |
| Known trends, constant, missing and short inputs | PASS | 21 new trend tests within 72 passing tests |
| Trusted reference and preserved preparation inputs | PASS | 210 slope-only comparisons, 72 original file hashes unchanged |
| Descriptive outputs, units, policy sensitivity and checkpoint boundary | PASS | Separate policy results, experimental annual completeness, inference fields absent |

## Estimator, time coordinates and units

For every pair of finite observations with later time `t[j] > t[i]`, calculate
`(y[j] - y[i]) / (t[j] - t[i])`; take the median of all such pair slopes.
The implementation is exact, not a sampled approximation. One shared kernel
serves both individual/regional series and all cells.

Time is mandatory and explicit:

- **Monthly:** subtract the first calendar-month ordinal and divide by 12.
  January 2001 to December 2024 spans 287/12 = 23.916667 calendar years.
  Calendar-month gaps retain their actual distances. Month aggregates are
  labeled by their year/month; provider sub-month clock offsets are not separate
  temporal measurements. This is a calendar-month year convention, not elapsed
  seconds divided by an assumed 365-day year.
- **Annual:** subtract the first actual calendar-year label. 2001 to 2024 spans
  23 years. Missing annual observations retain their original year positions;
  they are never compressed into adjacent indices or divided by twelve.
- **Missingness:** use only pairs whose two values are finite, without filling
  either observation. Invalid/repeated/reversed times or infinite observations
  raise input errors rather than producing an apparent zero slope.

The default shared guard is three finite observations, inherited from the
reviewed core. This is **computability only**, not a validated climate-record
length, coverage criterion or inference threshold. Two-point, singleton, empty
and all-missing records are insufficient under that guard; an explicit two-point
guard is possible in the low-level API. Scientific minimum record length remains
a later review decision. Constant valid records return numerical slope zero;
that is not evidence of stability or a significance classification.

Regional slopes come from the prepared area-weighted regional series. They are
**never calculated by averaging cell slopes**. The median of spatial cell slopes
below describes the distribution of cells, not an alternative regional estimate.

| Input | Descriptive slope units / interpretation |
| --- | --- |
| Temperature in K | K per elapsed year; same numeric slope in degrees Celsius per year |
| Soil moisture in kg m-2 | kg m-2 per elapsed year; no percentage conversion |
| Monthly precipitation amount in mm | Change in monthly accumulation per elapsed year |
| Annual precipitation total in mm | Change in annual accumulation per elapsed year; a different estimand from monthly amounts |
| NDVI in unitless values | NDVI per elapsed year; source scaling is unchanged |

Raw monthly values, the already-prepared full-reference calendar-month anomalies,
and complete annual summaries are different estimands. They need not have equal
slopes. No primary inferential basis or new seasonal correction was selected here.
For temperature and soil moisture, annual summaries are day-weighted means;
annual precipitation sums twelve monthly amounts; incomplete years stay missing.

## Regional results: twelve strict-policy inputs

Period: January 2001-December 2024; 288 monthly and 24 annual regional points.
Each row retains its own native grid and Stage 2 fixed spatial support. Numeric
slope direction is descriptive; these entries have no significance interpretation.
Monthly anomaly slopes use the existing Stage 2 full-reference calendar-month
baseline, not a newly fitted baseline for a selected window.

| Variable | Region | Raw monthly slope/year | Calendar-anomaly slope/year | Annual-summary slope/year | Slope units | Prepared cells |
| --- | --- | --- | --- | --- | --- | --- |
| air_temperature | nile_corridor | +0.047598638 | +0.030858817 | +0.025330383 | K per year | 102 |
| soil_moisture | nile_corridor | +0.000008500 | +0.002485710 | +0.008890434 | kg m-2 per year | 459 |
| precipitation | nile_corridor | +0.000684342 | +0.000487028 | +0.027554997 | mm per year | 3200 |
| vegetation_greenness | nile_corridor | +0.000099519 | +0.000117963 | +0.000123811 | 1 per year | 7302 |
| air_temperature | morocco_comparison | +0.044953502 | +0.031111736 | +0.033175364 | K per year | 80 |
| soil_moisture | morocco_comparison | -0.104636502 | -0.094120016 | -0.126120174 | kg m-2 per year | 287 |
| precipitation | morocco_comparison | -0.282964145 | -0.375750053 | -8.477351579 | mm per year | 2500 |
| vegetation_greenness | morocco_comparison | -0.000210735 | -0.000201454 | -0.000323103 | 1 per year | 3019 |
| air_temperature | sahel_comparison | -0.023212203 | -0.013312162 | -0.023441038 | K per year | 160 |
| soil_moisture | sahel_comparison | -0.018854443 | -0.031358824 | -0.026383742 | kg m-2 per year | 800 |
| precipitation | sahel_comparison | +0.001074650 | +0.024799162 | +2.603741107 | mm per year | 5000 |
| vegetation_greenness | sahel_comparison | +0.000538262 | +0.000673970 | +0.000973724 | 1 per year | 2961 |

For example, Nile temperature's raw monthly slope and annual mean slope differ;
this is not a factor-of-twelve conversion test because the input estimands differ.
The annual-axis regression uses known synthetic signals and independent reference
calculations. Likewise, Sahel rainfall's annual-total slope cannot be interpreted
as the slope of a mean monthly rate or compared by simply relabeling units.

## Sahel NDVI preparation-policy sensitivity

Strict 100% and Standard 100% are separate primary preparation comparisons.
Standard 95% remains experimental throughout the library outputs and notebook.
All regional monthly results below use the raw prepared monthly NDVI. Annual
regional results follow the existing twelve-month day-weighted summary definition.

| Policy | Eligible selected area | Eligible cells / 20000 | Regional monthly NDVI/year | Regional annual NDVI/year | Complete annual observations per eligible cell |
| --- | --- | --- | --- | --- | --- |
| strict_100 | 14.6948% | 2961 | +0.000538262 | +0.000973724 | 24 |
| standard_100 | 82.5869% | 16531 | +0.000603252 | +0.000953649 | 24 |
| standard_95 | 99.9751% | 19995 | +0.000567989 | +0.000901538 | 14-24 |

Standard 100% minus Strict 100% changes the regional monthly slope by
**+0.000064991 NDVI/year** and annual slope by **-0.000020075 NDVI/year**.
Standard 95% minus Standard 100% changes those slopes by **-0.000035264** and
**-0.000052111 NDVI/year**, respectively. Similar numeric slopes do not show
policy equivalence, and differences do not show statistical significance.
The policies sample different locations and marginal-quality observations.

| Policy | Median cell monthly NDVI/year | Median cell annual NDVI/year | Computable monthly cell slopes | Computable annual cell slopes | Excluded cells / 20000 |
| --- | --- | --- | --- | --- | --- |
| strict_100 | +0.000444445 | +0.000916301 | 2961 | 2961 | 17039 |
| standard_100 | +0.000509884 | +0.000946666 | 16531 | 16531 | 3469 |
| standard_95 | +0.000503616 | +0.000916044 | 19995 | 19995 | 5 |

The spatial median is included only as a descriptive distribution summary. Full
cell arrays contain slopes, valid counts, pair counts, valid spans and computable
flags. Excluded cells have missing slopes and are counted explicitly. Continuous
slope maps are shown without significance masks, categories or cell shares.

![Sahel regional preparation sensitivity](../../../data/derived/science/phase_3/sahel_policy_slopes.png)

![Continuous Sahel cell slopes](../../../data/derived/science/phase_3/sahel_cell_slopes.png)

### Experimental Standard 95% annual completeness

Its **5,157 incomplete eligible cell-years stay missing**. The existing review
annual arrays were loaded directly; the generator asserts that every cell-year
with fewer than twelve original valid months has a missing annual value. Annual
cell slopes use only the remaining complete years at their actual calendar-year
positions. They have **14-24 complete annual observations per eligible cell**,
not 24 artificially completed observations. All 19,995 eligible cells clear the
three-point computational guard; that does not make their annual records complete.

The experimental regional annual series has 24 values because every month has
some observed eligible area. Its monthly footprints still change, so those values
are not averages of one constant all-area sample. The separate annual regional
diagnostic over complete cell-years has slope **+0.000878540 NDVI/year**, versus
**+0.000901538** for the annual mean of changing-support monthly regional means.
These are separate estimands and can change geography between years. Neither
replaces the default. The larger annual-mean discrepancy in 2015 remains documented
in [the Standard 95% checkpoint](SAHEL_NDVI_STANDARD95_REVIEW.md).

## Validation and repair of inherited defects

The reviewed React branch at `486fe73551b3239bab172d26fe94979402c81e4e` contains
`data/nasa/analysis/trend.py`. Its finite-pair median slope method is retained,
with an explicit-time library boundary and shared scalar/grid implementation.
The broad legacy wrapper is not imported: it also invokes out-of-scope inference.
The existing historical probe reports remain unchanged, and that other branch's
code has not been rewritten or certified by this work.

| Check | Evidence / outcome |
| --- | --- |
| Known increasing/decreasing/constant slopes | Monthly and annual analytic slopes recovered; constant records return zero descriptively |
| Strong repeated seasonal cycle | Known zero, positive and negative slopes recovered on the tested complete synthetic record; not general validation of seasonality handling |
| Hand/rational reference | Exact hand median and independent rational pair calculations, including irregular times and an outlier |
| Missing observations | Preserve original time distances, valid counts and spans; reference agreement with masked regular records |
| Short/empty inputs | Zero/one/two finite points insufficient under the shared three-point guard; all-missing records return missing slope |
| Annual factor-of-twelve defect | Known annual slope +1 unit/year returns +1, not +12; correctly prepared annual means also match reference |
| Regional/grid minimum parity | With an explicit 60-point guard, both reject the inherited 48-sample fixture; the old inference threshold is not silently imposed on annual or monthly descriptive outputs |
| Batch/scalar parity | Same slopes and counts with single-cell, multi-cell and different computational batch sizes |
| Aggregation ordering | A controlled example confirms regional-series slope can differ from an average of cell slopes |
| Annual missingness | Incomplete cell-years remain NaN, and annual pair spacing retains real year labels |
| Invalid input handling | Reject duplicate/reversed/nonfinite times, unknown axes, infinite values and malformed shapes |
| Existing prepared artifacts | 72 file hashes unchanged; all 14 grid files reopened and matched to memory |
| Inference boundary | Result/grid fields checked for forbidden inference outputs; none present |

The [SciPy Theil-Sen documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.theilslopes.html)
defines the median-of-pairs estimator. For numerical reference, this validation
uses only [SciPy's slope-only routine](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.mstats.sen_seasonal_slopes.html)
with a single column. Its within-column median is the ordinary Sen slope at
regular sample positions. Monthly reference slopes are converted from per-sample
to per-year units by multiplying by twelve; annual references use actual one-year
row spacing. Missing rows stay masked in their original positions. This use does
not seasonally adjust the production output or generate intervals. No interval-
generating reference wrapper or hypothesis-test function was called.

Versions: NumPy 2.5.4, xarray 2026.9.0,
SciPy 1.18.0, netCDF4 1.7.5.1.post1.
The 210 reference comparisons cover all regional monthly/annual results,
regional anomaly/annual sensitivity results and six deterministic spread cells
per case and temporal basis. They are numerical checks, not a statistical sample
of scientific error. Maximum absolute difference is 5.55e-17; configured
absolute tolerance is 1e-10 with relative tolerance 1e-9.

## Tested limitations and remaining scientific decisions

- Reference agreement verifies the arithmetic, not measurement truth, climate
  representativeness, a stationary process or a correct causal interpretation.
- Raw monthly slopes can be sensitive to seasonal structure, window endpoints,
  serial dependence, missingness and outliers. Anomaly and annual comparisons
  describe different inputs and do not establish an optimal inferential basis.
- Complete-case strict NDVI retains little and geographically selective area;
  standard QA admits marginal observations. Experimental 95% additionally changes
  monthly spatial support and has incomplete cell-years. These limits survive a
  correct slope calculation.
- The three-point guard is not evidence that a short record supports a climate
  claim. A reviewed scientific record-length/coverage policy remains pending.
- The exact algorithm has quadratic pair work with respect to time samples.
  Temporary pair-value batches are bounded near two million float64 entries;
  calls above 2,048 time samples are explicitly rejected. The real-data run covers
  288 monthly points and 24 annual positions, not unlimited performance.
- Full run time was about 67.2 seconds in this local environment. The figure is
  a measured run, not a production latency guarantee.
- No intercept, fitted forecasting model, uncertainty calibration, inference,
  spatial labels/shares, period-window voting, HTTP integration or release flags
  are supplied by this checkpoint. Those later-phase gates remain open.

## Reproduction, outputs and review gate

From the repository root, using the existing prepared inputs:

```powershell
.\.venv\Scripts\python.exe -m pip install -r packages/science/requirements.txt
.\.venv\Scripts\python.exe tools/run_science_trends.py
.\.venv\Scripts\python.exe tools/validate_science_trends.py
.\.venv\Scripts\python.exe tools/run_science_trend_notebook.py
```

- Kernel: `packages/science/src/trend_estimation.py`.
- Candidate method choices: `packages/science/config/trend_policy.json`, revision
  `descriptive-ts-1.0`; separate from the unchanged Stage 2 policy.
- [Executed validation notebook](../notebooks/03_trend_validation.ipynb): synthetic
  recovery, all regional summaries, separate Sahel policy estimates, continuous
  cell slopes and experimental annual valid-count distributions.
- [Results](PHASE_3_RESULTS.json): numerical slopes, units, counts/spans, policy
  sensitivity, input/artifact hashes, software versions and code hashes.
- [Reference/preservation validation](PHASE_3_VALIDATION.json) and
  [test/regression evidence](PHASE_3_TESTS.json).
- `data/derived/science/phase_3/`: fourteen compact grid NetCDFs, two figures,
  manifest and preserved-input snapshot. Derived arrays are ignored by Git and
  reproducible from the commands above. No Stage 2 preparation is regenerated.

Phase 3 acceptance criteria are met for the stated descriptive scope. Recommend
reviewing the elapsed-time convention, three-point computational boundary, choice
of raw/anomaly/annual estimands, Sahel policy sensitivity and experimental annual
support before authorizing Phase 4. **Stop at this checkpoint.** The current
method, default preparation policy and inference release are not changed by a
recommendation to review the next phase.

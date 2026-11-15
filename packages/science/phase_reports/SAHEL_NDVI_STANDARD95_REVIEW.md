# Stage 2 checkpoint: Standard 95% NDVI monthly and annual review

Date: 15 November 2026. Branch: `codex/ml-statistics`.
Status: **review complete; Phase 3 decision pending**. Default: **unchanged**.

## Recommendation for Phase 3

Keep all three policies available: **Strict 100% as the unchanged default/control**,
**Standard 100% as the fixed-footprint comparison**, and **Standard 95% as an
experimental coverage sensitivity**. These results support carrying all three
into Phase 3 estimator validation, with explicit footprint labels. They do not
support promoting Standard 95% to the default or interpreting its annual regional
series as a constant-area average.

Standard 95% improves eligibility to 99.9751% of selected native-cell area, but
missing observations concentrate in particular months and years. Its regional
annual series has all 24 years, while **5,157 eligible cell-year
records remain incomplete and their cell annual values stay missing**. Phase 3
must retain monthly support diagnostics, compare common geography and test the
effect of the annual aggregation choice before interpreting temporal change.
Phase 3 has not started. No slopes or inference were computed.

## Inputs and preservation

Review scope: MOD13C2 Collection 6.1 NDVI in the Sahel rectangle [-5, 12, 5, 17],
January 2001 through December 2024; 20,000 cells and 288 months. NDVI is already
scaled and dimensionless. This review reads the existing original strict and
standard artifacts plus the existing experimental `standard_95.nc`. It does
not regenerate their values or modify QA, eligibility, weights or default policy.

The 95% rule requires at least 274 of 288 valid months per cell over the fixed
full reference. Standard 100% requires all 288. Both use the same standard QA.
The detailed-QA interpretation and marginal-data limitations remain those in the
[earlier policy checkpoint](SAHEL_NDVI_POLICY_CHECKPOINT.md); no new QA cutoff
or accuracy claim is introduced here. The experimental 90% and strict relaxed
stress cases also remain available in their original locations.

The run preserved **62 existing files** by before/after SHA-256,
including source cubes, policy, original outputs, earlier review artifacts and
the preprocessing notebook. New annual arrays and figures use a separate folder.

| Policy | Eligible cells | Eligible selected area | Missing eligible cell-months | Incomplete eligible cell-years | Incomplete regional annual records |
| --- | --- | --- | --- | --- | --- |
| Strict 100% (default) | 2961 | 14.6948% | 0 | 0 | 0 |
| Standard 100% | 16531 | 82.5869% | 0 | 0 | 0 |
| Standard 95% (experimental) | 19995 | 99.9751% | 5279 | 5157 | 0 |

Area denominators are full native spherical cells selected by their centres;
they are not exact polygon-intersection areas. Cell-count percentages and area
percentages differ with latitude. Structural exclusions are separate from
missing observations inside an eligible footprint.

## Missing observations by month, season and year

Standard 95% has **5,279 missing values out of
5,758,560 eligible cell-months** (0.091672%). Its five structurally
excluded cells represent another 1,440 cell-month positions, excluded from this
missingness denominator. There are 101 months with at least one eligible gap and
187 months with none. Across the 24 years, 3,464 eligible cells have at least one
gap; this is not the same count as incomplete cell-years, because a cell can be
incomplete in more than one year.

Each calendar-month row pools 24 occurrences across all eligible cells. Missing
area-time weights every constituent monthly cell by its native area; it does
not insert an NDVI value or weight by days. Annual NDVI uses day weights below.

| Calendar month | Missing eligible cell-months | Missing count fraction | Missing eligible area-time |
| --- | --- | --- | --- |
| 1 | 10 | 0.002084% | 0.002068% |
| 2 | 5 | 0.001042% | 0.001034% |
| 3 | 2 | 0.000417% | 0.000414% |
| 4 | 0 | 0.000000% | 0.000000% |
| 5 | 1 | 0.000208% | 0.000211% |
| 6 | 179 | 0.037301% | 0.037611% |
| 7 | 3459 | 0.720805% | 0.724541% |
| 8 | 1464 | 0.305076% | 0.305063% |
| 9 | 154 | 0.032091% | 0.031995% |
| 10 | 1 | 0.000208% | 0.000208% |
| 11 | 1 | 0.000208% | 0.000208% |
| 12 | 3 | 0.000625% | 0.000620% |

| Season | Missing eligible cell-months | Missing eligible area-time |
| --- | --- | --- |
| DJF | 18 | 0.001241% |
| MAM | 3 | 0.000208% |
| JJA | 5102 | 0.355738% |
| SON | 156 | 0.010804% |

DJF means December/January/February, MAM March–May, JJA June–August and SON
September–November. These are pooled calendar groups, not claims about local
wet/dry seasons or constructed winter years. **96.65% of eligible gaps occur in JJA**.
The JSON also supplies season counts within each calendar year (DJF there uses
January, February and December of that same year, not a continuous winter).

The year table below gives missingness, annual completeness and the annual
policy comparison. Each complete year contains 239,940 eligible cell-month
positions under Standard 95%. All years have 12 valid regional monthly means.
The annual NDVI columns use day-weighted monthly regional means, as explained below.

| Year | Missing eligible cell-months | Incomplete eligible cell-years | Missing eligible area-time | Worst monthly selected area | Annual NDVI 100% | Annual NDVI 95% | 95% minus 100% |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2001 | 77 | 75 | 0.032214% | 99.6831% | 0.202392 | 0.212204 | +0.009812 |
| 2002 | 646 | 640 | 0.268979% | 97.3665% | 0.192516 | 0.202262 | +0.009746 |
| 2003 | 36 | 36 | 0.015007% | 99.8600% | 0.207824 | 0.218965 | +0.011141 |
| 2004 | 132 | 121 | 0.054912% | 99.5211% | 0.198297 | 0.208473 | +0.010176 |
| 2005 | 29 | 27 | 0.012152% | 99.8692% | 0.201365 | 0.212011 | +0.010646 |
| 2006 | 246 | 240 | 0.102979% | 98.9389% | 0.201720 | 0.211899 | +0.010179 |
| 2007 | 245 | 245 | 0.102568% | 98.8247% | 0.207838 | 0.217395 | +0.009558 |
| 2008 | 86 | 85 | 0.035693% | 99.7612% | 0.203038 | 0.212947 | +0.009908 |
| 2009 | 162 | 154 | 0.067541% | 99.4944% | 0.197383 | 0.207592 | +0.010209 |
| 2010 | 518 | 509 | 0.216611% | 97.9191% | 0.207110 | 0.217964 | +0.010854 |
| 2011 | 80 | 76 | 0.033459% | 99.7487% | 0.201683 | 0.211422 | +0.009739 |
| 2012 | 73 | 72 | 0.030595% | 99.6733% | 0.205964 | 0.216244 | +0.010280 |
| 2013 | 109 | 109 | 0.045535% | 99.5892% | 0.206415 | 0.216649 | +0.010233 |
| 2014 | 228 | 214 | 0.095045% | 99.0690% | 0.200738 | 0.210486 | +0.009748 |
| 2015 | 1098 | 1092 | 0.461103% | 94.6698% | 0.205483 | 0.214566 | +0.009083 |
| 2016 | 106 | 105 | 0.044334% | 99.6134% | 0.206055 | 0.215747 | +0.009691 |
| 2017 | 42 | 35 | 0.017437% | 99.8657% | 0.204776 | 0.213787 | +0.009011 |
| 2018 | 175 | 174 | 0.072842% | 99.4861% | 0.209090 | 0.217819 | +0.008728 |
| 2019 | 92 | 91 | 0.038474% | 99.7537% | 0.211843 | 0.221270 | +0.009428 |
| 2020 | 385 | 368 | 0.161416% | 98.5716% | 0.220427 | 0.229480 | +0.009054 |
| 2021 | 94 | 90 | 0.039316% | 99.6682% | 0.217640 | 0.226054 | +0.008415 |
| 2022 | 164 | 158 | 0.068751% | 99.4772% | 0.218765 | 0.228252 | +0.009488 |
| 2023 | 134 | 125 | 0.055985% | 99.6796% | 0.218772 | 0.228115 | +0.009343 |
| 2024 | 322 | 316 | 0.135000% | 99.2308% | 0.237326 | 0.246559 | +0.009234 |

Every month is reported individually in the
[288-row coverage appendix](SAHEL_NDVI_STANDARD95_MONTHLY_COVERAGE.md), including
valid selected-area percentages for both policies, valid eligible area under
95%, missing eligible cell counts, and the two monthly regional NDVI values.
Full-precision values and all three policies are in the JSON evidence.

![Monthly gaps and policy differences](../../../data/derived/science/sahel_ndvi_annual_review/monthly_missingness_and_difference.png)

## Does the regional average change its spatial support?

**Yes for Standard 95%.** Its eligibility footprint stays fixed at 19,995 cells,
but a monthly regional mean uses only currently observed eligible cells and
renormalizes their spherical area weights. Standard 100%'s 16,531 cells remain
observed in every month, so that policy's contributing geography is constant.

In the worst month, **2015-07**, Standard 95% observes 18,942 cells,
with 1,053 eligible cells missing. Valid area is
**94.6698% of the selected rectangle cells**, or
**94.6933% of the eligible footprint**. A 95% per-cell
full-period threshold therefore does not guarantee 95% regional area in every month.
Standard 100% observes 82.5869% of selected native-cell area in every month.

Between successive months, the area switching into or out of Standard 95%'s
contributing set averages 0.1804% of selected area and reaches
5.4059%. This counts the symmetric difference of sets, not just
net area change. Its contributing-area latitude centroid ranges from
14.4997 to 14.6122 degrees north.
These diagnostics show that geography and weights change, even when the total
area change is small. They do not measure missing locations' unknown NDVI.

## Monthly and annual series: what changes and what does not?

Across 288 paired monthly regional values, Standard 95% minus Standard 100%
has a mean **0.009707 NDVI**, minimum
0.003775, maximum
0.022901, and RMSE
0.011334. These are descriptive differences, not error estimates.
On the **common Standard 100% footprint**, the Standard 95% source values
recover the original monthly and annual Standard 100% series to absolute tolerance
1e-12. Thus these contrasts arise from added locations and their availability,
not new measurements, rescaling, or different QA at shared observations.

Two annual estimates are explicitly distinguished:

1. **Annual mean of regional monthly means:** require twelve finite regional
   monthly values and average using actual calendar-month day counts. For Standard
   95%, each of those twelve monthly means can have a different footprint. All 24
   annual records are present for both policies; that does not establish complete
   spatial observations. This definition matches the original regional annual
   preparation rule, with an explicit changing-support caveat.
2. **Diagnostic annual mean over complete cell-years:** first require twelve
   original valid months in each cell-year and compute its day-weighted annual
   NDVI. Leave incomplete cell-years missing. Then average the complete cell
   annual values by native area. This uses a constant set of cells within each
   year but can change geography between years; it is not a replacement default.

Standard 95% has **5,157 incomplete eligible cell-years out of
479,880** (1.0746%), leaving
474,723 complete cell-year annual values. The five structurally
excluded cells are not counted as incomplete eligible records. Strict 100% and
Standard 100% each have no incomplete cell-years inside their own smaller footprints.

For the first annual definition, the mean difference over 24 paired years is
**0.009738 NDVI**, ranging from
0.008415 to 0.011141; RMSE is
0.009759. Requiring complete cell-years in Standard 95% changes its
annual estimate by a mean 0.000304 NDVI (monthly-regional definition
minus complete-cell definition), with maximum absolute difference
**0.003971** in 2015. This comparison changes the
spatial sample; it does not recover the unknown values in missing cells.

In 2015 specifically, 1,092 eligible cell-years are incomplete. The
Standard 95% annual regional mean is 0.214566, whereas the complete-cell-year diagnostic
is 0.210595. Its complete-cell-year area is only
94.4735% of selected native-cell area, compared with static 99.9751%
eligibility. A year with twelve regional points is not an all-area complete year.

![Annual series and completeness](../../../data/derived/science/sahel_ndvi_annual_review/annual_series_and_completeness.png)

## Preservation of missing values and scientific trade-offs

No interpolation, zero filling, forward filling, climatological reconstruction,
or rescaling was applied. Every finite prepared cell value equals its original
source value exactly. Incomplete cell annual values remain NaN. If an annual
regional input lacks a valid month, its annual value is NaN; if no complete
cell-years remain, their diagnostic regional mean is NaN. Zero mask values,
excluded weights and missing counts are bookkeeping, not replacement NDVI.

Broader eligibility reduces the geographic exclusion evident in strict data,
but adds marginal observations and time-varying spatial composition. Summer-
concentrated missingness and the uneven year distribution can affect seasonal
amplitude and annual averages. More retained area or higher NDVI does not prove
higher accuracy. Neither complete regional records nor this review establish
representativeness, missing-at-random behavior, measurement-error magnitude or
statistical significance.

## Phase 3 handoff and reproducibility

- Preserve Strict 100% as default/control and Standard 100% as the constant-
  footprint comparison. Continue to label their geographic restrictions.
- Carry Standard 95% only as an explicitly experimental monthly and annual
  sensitivity. Retain its 288 observed-area records and masks, plus incomplete
  cell-year flags. Compare the same dates and common spatial footprint.
- Keep the two annual definitions separate. Use 2015 and other low-coverage
  periods as preparation sensitivity checks in estimator validation. Any new
  monthly-area gate, seasonal completeness threshold, QA cutoff or default
  promotion needs an explicit versioned decision; none was imposed here.
- Test missing/short/seasonal inputs and explicit elapsed-year units in Phase 3
  before interpreting slopes. Leave inference and application readiness unchanged.

Reproduce this read-only-input review from the repository root:
`.\.venv\Scripts\python.exe tools/review_sahel_ndvi_annual.py`.
It requires the already prepared original and experimental files; it does not
rebuild them. New arrays/figures are in
`data/derived/science/sahel_ndvi_annual_review/` (ignored by Git).
The three `*_annual_review.nc` files store complete/incomplete cell-year counts,
missing-preserving cell annual values, both annual regional estimates and area
diagnostics. The original three preprocessing policies remain available unchanged.

Evidence: [full JSON](SAHEL_NDVI_STANDARD95_REVIEW.json),
[all monthly coverage records](SAHEL_NDVI_STANDARD95_MONTHLY_COVERAGE.md),
[earlier QA checkpoint](SAHEL_NDVI_POLICY_CHECKPOINT.md).
The generator verifies original hashes, source-value identity, QA/support masks,
canonical annual reproduction, common-footprint monthly/annual agreement, year
accounting and NetCDF reopening. Validation command:
`.\.venv\Scripts\python.exe -m unittest discover -s packages/science/tests -q`.
**51 tests pass**, including seven new annual/completeness checks.

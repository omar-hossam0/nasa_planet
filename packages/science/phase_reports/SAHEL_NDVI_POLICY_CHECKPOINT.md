# Stage 2 checkpoint: Sahel MOD13C2 NDVI quality and coverage

Date: 15 November 2026. Branch: `codex/ml-statistics`.
Status: **review complete; recommendations pending owner decision**.
Scope: preparation and descriptive sensitivity only. Stage 3 has not started.

## Decision recommended

Carry **strict 100% as the unchanged default/control**, **standard 100% as
the fixed-footprint comparison**, and **standard 95% as an experimental
spatial-coverage sensitivity** into Stage 3 method development. Do not promote
standard 95% to the default on the basis of area retention. Defer standard 90%:
it adds only two cells to standard 95%, with a maximum monthly NDVI difference
of 0.00002462. Retain strict 95% and 90% as diagnostic stress cases rather than
primary regional inputs because their monthly spatial support varies much more.

The default policy file, original strict/standard files, original Stage 2
reports/notebook and all source measurement cubes are unchanged. The run checked
44 original files by SHA-256 before and after processing. The existing policy's
recorded review status is also unchanged; this checkpoint does not grant approval.
There are no estimated slopes, p-values, confidence intervals or significance claims.

## What was examined

The Sahel rectangle is longitude -5 to 5 degrees and latitude 12 to 17 degrees.
`MOD13C2_Sahel_2001_2024.nc` contains 288 months, January 2001–December 2024,
and 100 × 200 = 20,000 cells. All 5,760,000 source NDVI values are finite before
QA. NDVI is a dimensionless vegetation-greenness index; it is already scaled
in this delivered cube and was not scaled again.

Quality acceptance and coverage eligibility are separate decisions:

- **Strict QA:** MODLAND bits 0–1 equal 0 and reliability equal 0, plus valid
  NDVI/range and QA words. It accepts 5,450,143 observations, 94.6205% of all
  source cell-months.
- **Standard QA:** MODLAND bits 0–1 in {0,1} and reliability in {0,1}, with
  the same validity checks. It accepts 5,754,499 observations, 99.9045%.
  This is the existing team's “standard” policy, not a NASA certification.
- **100% coverage:** keep a cell only if it passes that QA mode in all 288
  reference months. This reproduces the existing complete-case outputs.
- **95% coverage:** at least `ceil(0.95 × 288) = 274` valid months per cell;
  at most 14 months may be missing.
- **90% coverage:** at least `ceil(0.90 × 288) = 260` valid months per cell;
  at most 28 months may be missing.

The last two are experimental team thresholds. They do **not** require 95% or
90% of the region to be observed every month, nor guarantee seasonal completeness.
The eligibility footprint is selected once over the full reference period; it
would need a new version if that reference changes. It must not be silently
reselected for shorter trend windows.

## QA documentation verification

Checked the stored official [MODIS Collection 6.1 user guide](https://lpdaac.usgs.gov/documents/621/MOD13_User_Guide_V61.pdf),
including visual inspection of PDF pages 27–28. Local copy:
`data/nasa/expanded_v2/docs/MOD13_User_Guide_V61.pdf`.
Its SHA-256 matches the preparation policy:
`7440d485fef25e85c19752c553989d7af33698f2f606cc0b50cf298012f85a0a`.

| Guide location (PDF page; printed page) | Interpretation used |
|---|---|
| Table 5 (18; 15) | MODLAND 0 is good; 1 requires other QA checks; 2 is probably cloudy; 3 is unproduced. Decode usefulness, aerosol, adjacent-cloud, BRDF, mixed-cloud and land/water separately. |
| Usefulness description (19; 16) | Scores span 0–12, with 13–15 reserved for unusable/faulty/unprocessed cases. Preserve observed numeric scores rather than inventing acceptance cutoffs. |
| Section 8.3.2 / Table 17 (27; 24) | CMG bits 14–15 describe the fraction of contributing finer pixels: ≤25%, >25–50%, >50–75%, >75%. They are not snow/shadow flags for this product. |
| Table 18 (28; 25) | Reliability 1 permits conditional use after other QA checks; 4 indicates historical estimation. |
| Table 19 / section 9 (28; 25) | Verify ranges/fill and provider scaling; monthly composites can include upstream historical climatology. |
| Section 9.3.2 (29; 26) | MOD13C2 uses the MOD13C1 QA definitions, including the CMG exceptions. |

Both existing modes reject all reliability-4 observations (5,267 in the source),
fill, cloudy and snow reliability codes, and MODLAND 2/3. These checks do not
prove that every monthly composite is free of upstream estimated contributions:
only the delivered monthly summary QA fields are available for that check.
The other product layers such as the number of finer contributing pixels were
not delivered in this cube. The existing modes do not separately screen the
detailed usefulness, aerosol, adjacent-cloud, land/water or CMG coverage fields.

### What the extra marginal observations contain

“Marginal” below means **standard accepted and strict rejected** at the same
cell and month. There are **304,356** such observations (5.2840% of all source
cell-months). Of these, 304,031 have reliability 1, while 325 have reliability 0
but MODLAND 1. Reliability alone would miss those 325. All have usefulness
scores 1–9; none have the reserved unusable scores 13–15 or a mixed-cloud flag.

| Detailed flag among these 304,356 observations | Count | Share of marginal observations |
|---|---:|---:|
| Intermediate aerosol | 159,313 | 52.34% |
| High aerosol | 5,652 | 1.86% |
| Aerosol climatology | 1,010 | 0.33% |
| Low aerosol | 138,381 | 45.47% |
| Adjacent-cloud flag set | 38,789 | 12.74% |
| CMG finer-pixel contribution ≤25% | 55,510 | 18.24% |
| CMG finer-pixel contribution >25–50% | 56,212 | 18.47% |
| CMG finer-pixel contribution >50–75% | 81,811 | 26.88% |
| CMG finer-pixel contribution >75% | 110,823 | 36.41% |
| Coast/shoreline or shallow inland-water mask | 5,783 | 1.90% |

These fields overlap; the rows must not be summed as exclusive rejection reasons.
Even strict accepted data include 2,529 adjacent-cloud flags and land/water codes
other than pure land. Thus strict QA is not an independent validation reference.
No additional flag cutoff was imposed, and no flag was treated as an error
probability or quality weight. Marginal data are conditionally usable according
to the guide, but this evidence does not establish equal accuracy to good data.

## Monthly and seasonal quality distributions

Acceptance percentages below use **all 20,000 source cells × 24 occurrences
of the calendar month** as the denominator, before spatial eligibility.

| Calendar month | Strict accepted | Standard accepted | Added marginal share of source |
|---|---:|---:|---:|
| January | 99.4054% | 99.9912% | 0.5858% |
| February | 99.4319% | 99.9948% | 0.5629% |
| March | 97.9006% | 99.9975% | 2.0969% |
| April | 94.8954% | 99.9990% | 5.1035% |
| May | 98.9785% | 99.9992% | 1.0206% |
| June | 97.8990% | 99.9619% | 2.0629% |
| July | 90.4750% | 99.2773% | 8.8023% |
| August | 74.4331% | 99.6871% | 25.2540% |
| September | 85.5433% | 99.9604% | 14.4171% |
| October | 97.0723% | 99.9952% | 2.9229% |
| November | 99.7006% | 99.9960% | 0.2954% |
| December | 99.7112% | 99.9944% | 0.2831% |

DJF = December–February, MAM = March–May, JJA = June–August, SON =
September–November. Each group pools 72 calendar-month records over 24 years;
these labels do not assert a local wet/dry-season boundary or construct winter years.

| Season | Strict accepted, all source | Standard accepted, all source | Marginal count | Adjacent cloud among marginal | CMG ≤25% among marginal |
|---|---:|---:|---:|---:|---:|
| DJF | 99.5162% | 99.9935% | 6,873 | 0.15% | 0.74% |
| MAM | 97.2582% | 99.9985% | 39,461 | 0.51% | 0.44% |
| JJA | 87.6024% | 99.6421% | 173,372 | 17.58% | 25.39% |
| SON | 94.1054% | 99.9839% | 84,650 | 9.56% | 13.30% |

The extra observations and their detailed flags vary strongly by season. JJA
contains 56.96% of all added marginal observations. Treating those observations
as exchangeable with other months could distort seasonal comparisons. Complete
numeric flag histograms, NDVI distributions and area-time-weighted flag shares
for each month/season and QA population are in
[SAHEL_NDVI_QA_DISTRIBUTIONS.json](SAHEL_NDVI_QA_DISTRIBUTIONS.json).

## Spatial coverage and prepared regional series

Area percentages use **all selected full native-cell spherical areas** as their
denominator; they are not exact polygon-intersection areas or cell-count percentages.
The 100% rows reproduce the original masks exactly and their regional series to
absolute tolerance 1e-12 NDVI. Original files were read, not regenerated.

| QA / required months | Eligible cells / 20,000 | Eligible area | Mean monthly observed area | Minimum monthly observed area | Mean monthly regional NDVI |
|---|---:|---:|---:|---:|---:|
| Strict / 288 (100%) | 2,961 | 14.6948% | 14.6948% | 14.6948% | 0.147714 |
| Strict / 274 (95%) | 11,089 | 55.2042% | 54.5117% | 44.3180% | 0.164299 |
| Strict / 260 (90%) | 15,749 | 78.5884% | 76.1402% | 55.3583% | 0.187931 |
| Standard / 288 (100%) | 16,531 | 82.5869% | 82.5869% | 82.5869% | 0.207455 |
| Standard / 274 (95%) | 19,995 | 99.9751% | 99.8832% | 94.6698% | 0.217162 |
| Standard / 260 (90%) | 19,997 | 99.9851% | 99.8925% | 94.6748% | 0.217168 |

Strict 100% retains only **0.5486% of the southern half's area** (latitudes
below 14.5°) and 28.4407% of the northern half's area. Standard 100% retains
74.0700% and 90.8627%, respectively. Strict 100%'s retained-area latitude centroid
is 16.1345°N; standard 100%'s is 14.6988°N. The strict subset substantially
overrepresents the north. These are geographic halves, not inferred land-cover classes.

Across the same 288 months, standard 100% regional NDVI exceeds strict 100%
by a mean 0.059742, with mean differences DJF 0.038554, MAM 0.027305,
JJA 0.078223 and SON 0.094885. On the **common strict-100% footprint**, applying
standard QA recovers the strict series within 1e-12: accepted observations there
already pass both modes. The full-series difference therefore reflects which
additional locations can contribute under standard QA, rather than a direct
measurement-error comparison on paired observations. A higher NDVI is not evidence
that a policy is more accurate.

Standard 95% adds 3,464 cells to standard 100%; its regional series is higher
by a mean 0.009707 and at most 0.022901 NDVI. Standard 90% adds 3,466 cells
to standard 100%. Its mean difference from standard 95% is 0.00000567 NDVI.
All six regional series have 288 finite months; this does not imply complete
cell observations. Marginal observations contribute 4.5135% of standard 100%'s
observed area-time, 5.3105% for standard 95%, and 5.3135% for standard 90%.

![Eligible cell footprints](../../../data/derived/science/sahel_ndvi_policy_review/eligible_footprints.png)

![Regional NDVI series and monthly support](../../../data/derived/science/sahel_ndvi_policy_review/monthly_series_and_support.png)

## Missingness within the experimental footprints

No values were interpolated, carried forward, replaced by climatology or
reconstructed. For each month the regional estimate is
`sum(area × observed NDVI) / sum(area of observed eligible cells)`.
Only original QA-valid values enter this sum. Missing cell NDVI stays NaN;
if nothing contributes, the regional value is NaN. Zeros in masks or excluded
weights are bookkeeping, never replacement NDVI. The eligible footprint is static;
the contributing footprint and its normalized weights can change monthly.

The percentages below are **missing area-time / eligible footprint area-time**
within each season, excluding cells ineligible for that particular policy. Each
season has 72 months. They are not percentages of the entire rectangle. Both
100% policies have zero missingness inside their smaller retained footprints.

| Experimental policy | DJF missing | MAM missing | JJA missing | SON missing |
|---|---:|---:|---:|---:|
| Strict 95% | 0.0801% | 0.6691% | 2.3800% | 1.8889% |
| Strict 90% | 0.1512% | 1.4346% | 6.9434% | 3.9317% |
| Standard 95% | 0.001241% | 0.000208% | 0.355738% | 0.010804% |
| Standard 90% | 0.001448% | 0.000277% | 0.357288% | 0.011356% |

Standard 95% has 5,279 missing eligible cell-months: DJF 18, MAM 3, JJA
5,102, SON 156. Standard 90% has 5,314: DJF 21, MAM 4, JJA 5,125, SON
164. Count-based missingness and area-weighted missingness differ slightly
because native cell areas vary with latitude. Both denominators are in the metrics.

Full-period coverage can conceal concentrated seasonal gaps. The least-complete
JJA cell has 84.72% of its 72 JJA observations under standard 95%, and 80.56%
under standard 90%. Strict 95% reaches 80.56%; strict 90% reaches 62.50%.
No eligible cell in these actual cases lacks every observation of an entire
calendar month. This is an observed result, not a guarantee provided by a
full-period 90%/95% threshold.

![Calendar-month QA acceptance and seasonal missingness](../../../data/derived/science/sahel_ndvi_policy_review/calendar_month_quality.png)

## Changing spatial support and potential bias

| Policy | Worst observed fraction of its eligible footprint | Worst month | Months below 95% of eligible area | Largest area switching membership between successive months, % of selected area |
|---|---:|---|---:|---:|
| Strict 100% | 100% | Constant | 0 | 0% |
| Standard 100% | 100% | Constant | 0 | 0% |
| Strict 95% | 80.2801% | 2023-09 | 25 | 12.5470% |
| Strict 90% | 70.4408% | 2010-08 | 61 | 23.5281% |
| Standard 95% | 94.6933% | 2015-07 | 1 | 5.4059% |
| Standard 90% | 94.6889% | 2015-07 | 1 | 5.4059% |

“Switching” is the area in the symmetric difference of the two monthly observed
sets, not merely their net area difference. Standard 95%'s contributing latitude
centroid ranges from 14.4997°N to 14.6122°N. Its mean observed eligible fraction
is 99.9189% in 2001–2012 and 99.8971% in 2013–2024. These descriptive comparisons
show that support is not perfectly stable over time. They do not establish a
trend in missingness.

The evidence identifies several possible biases, without measuring their true error:

- **Spatial selection:** requiring perfect strict QA removes almost the entire
  southern half and changes the regional greenness distribution. No complete-case
  series should be described as an unqualified mean of the whole Sahel rectangle.
- **Seasonal selection:** rejection and marginal acceptance concentrate in
  July–September. Missingness need not be random with respect to NDVI or conditions
  affecting retrieval. Removing those observations can change seasonal amplitude.
- **Marginal retrieval quality:** aerosol, adjacent-cloud and low finer-pixel
  contribution flags warrant sensitivity checks. Their effect on actual NDVI error
  cannot be calibrated using these summary flags alone.
- **Monthly composition:** relaxed eligibility changes the set and weight of cells
  contributing to regional NDVI. Support changes can resemble temporal variation;
  the missing locations' contemporaneous NDVI is unknown, so the direction and
  magnitude of that contribution cannot be recovered without additional evidence.
- **Mixed surfaces and upstream processing:** this is a bbox-based CMG series,
  including some shoreline/water flags. No new land mask was applied. Excluding
  flagged historical estimates does not audit every upstream compositing input.

No experimental annual series or anomalies were substituted into the default
pipeline. A future annual summary of a changing-support regional series must
retain that interpretation. Per-cell annual summaries must still require all
twelve original valid months; the experiments authorize no seasonal gap filling.

## Stage 3 handoff recommendation and remaining gates

| Policy | Recommended role in Stage 3 | Reason / condition |
|---|---|---|
| Strict 100% | Preserve as default and restricted-footprint control | Reproducible fixed support, but only 14.69% of area and strong northern selection. Label its footprint. |
| Standard 100% | Proceed as the principal fixed-support comparison | 82.59% retained area and no monthly composition change inside it; marginal-quality limitations remain explicit. This is not a default change. |
| Standard 95% | Proceed as an experimental sensitivity alongside standard 100% | Nearly all-area eligibility with small average gaps, but flag 2015-07 and carry monthly masks/areas into every result. Require a common-footprint comparison and seasonal coverage checks before interpreting slopes. |
| Standard 90% | Defer from the core handoff; retain generated evidence | Two extra cells and negligible series difference versus 95% do not justify a looser core coverage choice here. |
| Strict 95% / 90% | Retain as diagnostic stress cases | Reveal how strict QA interacts with geography and season; larger monthly support changes make them unsuitable as the primary whole-rectangle series. |

For Stage 3, freeze named reference footprints, preserve explicit elapsed-year
time coordinates, verify estimator behavior with missing/seasonal data and compare
like-for-like windows on common support. Any additional detailed-QA exclusion or
monthly-area gate needs a separate version and review; none was invented here.
Neither greater retention nor agreement among policies establishes accuracy,
representativeness, independence or statistical significance. This checkpoint
recommends a handoff; it does not start Stage 3 or approve an inference method.

## Outputs, reproducibility and validation

- Numerical implementation: `packages/science/src/qa_policy_review.py`.
- Reproduction: from the repository root run
  `.\.venv\Scripts\python.exe tools/review_sahel_ndvi.py`.
  This requires the existing original strict and standard Stage 2 artifacts;
  the review deliberately refuses to regenerate or replace a missing baseline.
- Tests: `.\.venv\Scripts\python.exe -m unittest discover -s packages/science/tests -q`.
  **44 tests passed**: 38 existing and 6 controlled experiment tests covering
  exact 288-month boundaries, missingness, observed-area weighting, empty support,
  invalid inputs and CMG-specific decoding.
- [Policy metrics](SAHEL_NDVI_POLICY_METRICS.json): per-case area/cell support,
  all 288 monthly regional values and support diagnostics, monthly/seasonal
  missingness, per-cell completeness distributions, geographic halves, descriptive
  series differences, artifact/source hashes and preservation evidence.
- [QA distributions](SAHEL_NDVI_QA_DISTRIBUTIONS.json): complete decoded flag
  counts and shares for strict, standard and added marginal observations, by
  calendar month and season, with count and area-time denominators.
- Separate NetCDF outputs and three figures:
  `data/derived/science/sahel_ndvi_policy_review/`. Cases are `strict_100`,
  `strict_95`, `strict_90`, `standard_100`, `standard_95`, `standard_90`.
  Derived files are ignored by Git and can be recreated with the command above.
- NetCDF fields include `cell_monthly`, `regional_monthly`, `eligible_support`,
  `observed_support`, `normalized_observed_weight`, `native_cell_solid_angle`,
  `valid_reference_month_count`, `observed_cell_count`, both monthly area fractions,
  `qa_accepted`, and the unchanged source `VI_Quality` / `pixel_reliability` fields.
  Each artifact identifies its QA mode, full reference, required count, source
  hash, QA-policy hash, experimental status and absence of inference.

The generator independently checked original 100% masks/means, source-value
identity at every retained observation, exact missing-value masks, common-footprint
means, NetCDF reopen consistency and unchanged original hashes. Figures were
visually inspected. Source cube SHA-256:
`063eeb3002c6f769b2389236626569d60f053a2a08f92500597d837222b1b02a`.

# Phase 5 checkpoint: descriptive spatial trend analysis

**DONE_WAITING_APPROVAL. Phase 5 descriptive implementation passes; Phase 6 has not started. Inference remains disabled.**

The explicit user approval is recorded in [PHASE_5_APPROVAL.md](PHASE_5_APPROVAL.md). This revises Phase 5 to descriptive analysis after the failed Phase 4 research; it does not relax any inference acceptance criteria or approve inference release. No repository rule requires a second scope approval.

## Implemented scope

All twelve strict variable/region cases and the two additional validated Sahel NDVI cases (Standard 100% and experimental Standard 95%) are processed. These are the fourteen Phase 3 cases; no new preparation or default is introduced. Policy sensitivities are confined to the validated Sahel three-policy set.

Monthly and annual cell slopes reuse the exact validated Sen kernel. Regional slopes are computed separately from prepared regional series. Monthly coordinates use calendar-month differences divided by twelve; annual coordinates use actual calendar years. Missing values and incomplete Standard 95% cell-years remain missing. The minimum of three finite observations is computational only, not scientific record-length adequacy.

Each native-coordinate NetCDF contains four windows (2001–2024, 2001–2012, 2013–2024, 2005–2024), monthly/annual slopes, n_valid, valid spans, pair counts, direction codes, comparison with the actual full-period sign, eligible support and observed-month fractions. Each case has an annual slope/direction/footprint/coverage map. The executed [notebook](../notebooks/05_descriptive_spatial.ipynb) displays all three Sahel policies and period results.

Direction codes: -1 negative; 1 positive; 2 exactly zero; 0 unavailable. Outside-support cells also display unavailable, distinguished by the eligibility map. A near-zero finite slope retains its actual sign; exact zero is not evidence of stability. Reference agreement codes: 1 agrees, 0 differs, -1 unavailable.

Cell percentages divide by all preparation-eligible cells, including eligible cells with unavailable slopes. Excluded cells are counted separately. Area coverage divides the eligible spherical-cell solid angle by all selected-cell solid angles, not by cell count. No category is a significance classification.

## Real NASA full-period annual examples

Slopes are changes per elapsed year. Precipitation annual values are complete annual accumulated mm; their slope describes changes in annual accumulation, not a sum of source rates. Temperature retains K, soil moisture kg m-2, NDVI dimensionless 1.

| Variable / region / policy | Regional annual slope | Units | Eligible area % of selected | Eligible cells | Excluded | Positive % of eligible | Unavailable % of eligible |
|---|---|---|---|---|---|---|---|
| air_temperature / nile_corridor / strict_100 | 0.0253303833 | K per year | 100.0000 | 102 | 0 | 100.000 | 0.000 |
| soil_moisture / nile_corridor / strict_100 | 0.00889043384 | kg m-2 per year | 89.9778 | 459 | 53 | 63.399 | 0.000 |
| precipitation / nile_corridor / strict_100 | 0.027554997 | mm per year | 100.0000 | 3200 | 0 | 79.594 | 0.000 |
| vegetation_greenness / nile_corridor / strict_100 | 0.000123810555 | 1 per year | 57.5034 | 7302 | 5498 | 29.951 | 0.000 |
| air_temperature / morocco_comparison / strict_100 | 0.0331753642 | K per year | 100.0000 | 80 | 0 | 98.750 | 0.000 |
| soil_moisture / morocco_comparison / strict_100 | -0.126120174 | kg m-2 per year | 72.1338 | 287 | 113 | 0.697 | 0.000 |
| precipitation / morocco_comparison / strict_100 | -8.47735158 | mm per year | 100.0000 | 2500 | 0 | 0.000 | 0.000 |
| vegetation_greenness / morocco_comparison / strict_100 | -0.000323102513 | 1 per year | 30.6244 | 3019 | 6981 | 55.946 | 0.000 |
| air_temperature / sahel_comparison / strict_100 | -0.0234410378 | K per year | 100.0000 | 160 | 0 | 3.750 | 0.000 |
| soil_moisture / sahel_comparison / strict_100 | -0.0263837417 | kg m-2 per year | 100.0000 | 800 | 0 | 15.625 | 0.000 |
| precipitation / sahel_comparison / strict_100 | 2.60374111 | mm per year | 100.0000 | 5000 | 0 | 83.720 | 0.000 |
| vegetation_greenness / sahel_comparison / strict_100 | 0.00097372429 | 1 per year | 14.6948 | 2961 | 17039 | 97.197 | 0.000 |
| vegetation_greenness / sahel_comparison / standard_100 | 0.000953648849 | 1 per year | 82.5869 | 16531 | 3469 | 84.901 | 0.000 |
| vegetation_greenness / sahel_comparison / standard_95 | 0.000901537752 | 1 per year | 99.9751 | 19995 | 5 | 82.201 | 0.000 |

Complete counts for positive, negative, exactly zero and unavailable, plus all monthly/annual period results and regional annual observations, are in [PHASE_5_RESULTS.json](PHASE_5_RESULTS.json). These signs describe estimated change only.

## Preparation-policy comparisons and limits

- standard_100 versus strict_100: common 2961 cells; gained 13570; lost 0; common annual computable 2961; mean common-cell slope difference 0 NDVI/year. Native-grid common/gained/lost masks are saved separately.
- standard_95 versus standard_100: common 16531 cells; gained 3464; lost 0; common annual computable 16531; mean common-cell slope difference 0 NDVI/year. Native-grid common/gained/lost masks are saved separately.

Regional slopes and represented geography differ across policies. Identical common-cell slopes do not make regional slopes interchangeable: added locations change the regional aggregate. These comparisons are not causal attribution or calibrated uncertainty.

Standard 95% preserves **5157 missing eligible cell-years**. Regional annual means aggregate changing-support monthly regional means; they are distinct from averages of complete cell-years. Monthly valid-area fractions for all 288 months remain visible in JSON. Strict 100% remains the default, Standard 100% the fixed-support comparison, and Standard 95% experimental only.

Coverage describes centre-selected native rectangular cells, not exact polygon intersections. Low strict NDVI retention can select unrepresentative land. A region-level estimate describes its actual retained footprint. Seasonal raw monthly slopes, short windows and missing-year patterns limit interpretation. No imputation, reweighting policy change or annual-completeness relaxation was introduced.

## Period sensitivity

Every window is recalculated from eligible observed values at their actual coordinates with fixed reference-period preparation support. Counts/spans and unavailable results are explicit. Cell directions compare to that same cell’s actual 2001–2024 slope; regional directions compare to the actual full regional slope, never the majority of windows. Window sensitivity is descriptive, not confidence or a promised reversal.

| Sahel NDVI policy | Period | Annual observations | Annual slope (NDVI/year) | Regional sign agrees full period |
|---|---|---|---|---|
| strict_100 | 2001–2024 | 24 | 0.00097372429 | True |
| strict_100 | 2001–2012 | 12 | 0.000804416002 | True |
| strict_100 | 2013–2024 | 12 | 0.00232433791 | True |
| strict_100 | 2005–2024 | 20 | 0.00116831277 | True |
| standard_100 | 2001–2024 | 24 | 0.000953648849 | True |
| standard_100 | 2001–2012 | 12 | 0.0005039894 | True |
| standard_100 | 2013–2024 | 12 | 0.00216962825 | True |
| standard_100 | 2005–2024 | 20 | 0.00106327625 | True |
| standard_95 | 2001–2024 | 24 | 0.000901537752 | True |
| standard_95 | 2001–2012 | 12 | 0.000394309272 | True |
| standard_95 | 2013–2024 | 12 | 0.00212060235 | True |
| standard_95 | 2005–2024 | 20 | 0.00102614026 | True |

## Validation, failures and preservation

**118 tests pass**, including the 110 earlier regressions and eight new fixture tests. Zero test failures/errors. All 28 full-period cell-grid/regional comparisons match preserved Phase 3 results exactly. Fourteen NetCDF round trips pass. 112 independent slope-only SciPy regional-window checks pass. Counts, denominators, coordinates, missing annual records, actual-reference signs, JSON nulls and absence of inference fields are checked.

All **3687 protected existing files** are unchanged by SHA-256, including NASA measurements, preparation policies/outputs, validated slopes and failed-method evidence. Source/method hashes are in results. The previous notebooks and reports are preserved. The new notebook executed all four code cells without errors; the Sahel experimental map was visually inspected.

An initial rendering run failed because Colorbar.set_ticks required labels as a keyword. This was corrected before the successful generation; no scientific inputs or method parameters changed. No unresolved numerical/test failure remains. Scientific inference remains a failed-validation limitation, not a Phase 5 test success.

## Artifacts and integration boundary

Reusable JSON is [PHASE_5_RESULTS.json](PHASE_5_RESULTS.json). Local native-grid NetCDFs, map PNGs and spatial policy masks are under `data/derived/science_spatial/phase_5/`; file identities are in [PHASE_5_VALIDATION.json](PHASE_5_VALIDATION.json). Derived arrays are ignored by Git; reproduce them with the commands below. JSON results retain source artifact identities, units, policy flags, limitations and monthly coverage. The numerical module imports only the validated slope module; no HTTP contract or production API was changed.

Inference is explicitly `disabled_failed_validation`, application_release is false, and Phase 6 is not started. No p-values, confidence intervals, FDR decisions or significance/stability labels are generated. Existing inference release flags are untouched.

```powershell
.\.venv\Scripts\python.exe tools/run_science_spatial.py
.\.venv\Scripts\python.exe tools/validate_science_spatial.py
.\.venv\Scripts\python.exe tools/run_science_spatial_notebook.py
.\.venv\Scripts\python.exe tools/checkpoint_science_spatial.py
```

Pending: owner review of this descriptive checkpoint, approval before Phase 6, and backend/frontend coordination of final payloads and map delivery. No integration, deployment or inference release is implied. **Stop here for user review.**

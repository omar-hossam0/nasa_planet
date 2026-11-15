# Trend Detective: verified project data pack

Original Egypt pack scope: two variables, monthly January 2001–December 2024, bounding rectangle 24–36 E and 22–32 N. Expanded v2 scope (see the regional section below and docs/architecture/scope.v2.json): four variables across three regions. This is a geographic rectangle around Egypt, not a national-boundary mask. Includes adjacent land and sea. Both source grids are retained separately.

## Start here
- measurements/M2TMNXSLV_Egypt_2001_2024.nc — actual 288-month air-temperature cube, T2M, kelvin. Subtract 273.15 to display Celsius; temperature-change units are numerically identical.
- measurements/GLDAS_NOAH025_M_Egypt_2001_2024.nc — actual 288-month upper-soil-moisture cube, SoilMoi0_10cm_inst, kg m-2. Not a percentage.
- measurements/<product>/<month>.nc — all 576 individual regional subsets with source-granule attribution.
- frontend/T2M.json and frontend/SoilMoi0_10cm_inst.json — identical values in a browser-friendly format with explicit dimension order and nulls for missing data. Do not treat nulls as zeros.
- runtime_catalog.json — legacy source-ingestion registry for the original two-variable Egypt pack. Expanded input mapping is in `../../docs/architecture/scope.v2.json`; neither registry certifies a statistical method or application.
- validation_report.json — tests on every month, units, dimensions, missing data, native coordinates and file hashes. This verifies ingestion, not scientific trend conclusions.
- source_lineage.json and manifests/ — source inventory and local hashes for every month.
- rag/corpus.jsonl — official product and method-documentation chunks with citations. NASA source docs in rag/sources/ and docs/; software-method docs in methods/.
- rag/retrieve.py — minimal offline lexical retrieval; Arabic aliases are limited. This is not a finished or evaluated production RAG system.
- rag/AI_CONTRACT.md and rag/evaluation_questions.json — project-authored behavior requirements and an unexecuted model-evaluation set.
- rag/cairo_temperature_monthly.csv — separate NASA POWER point sample; do not use it as the regional cube or conflate its Celsius units with MERRA-2 kelvin.

## Python example
    import xarray as xr
    ds = xr.open_dataset("measurements/M2TMNXSLV_Egypt_2001_2024.nc")
    temperature_c = ds["T2M"] - 273.15

## Re-download
Install requirements.txt. Run download_recoverable.py in this directory. Enter Earthdata credentials only in its local terminal. Existing monthly files are reused. regional_worker.py contains the regional selection and the GLDAS ancillary-variable workaround. Credentials stay in memory. No passwords or tokens are included in this pack.

## Regional expanded data (v2 scope, 14 November 2026)

The competition scope is now **4 variables x 3 regions x 288 months (2001-01..2024-12), 12/12 cubes verified**.

- measurements/<product>_<Region>_2001_2024.nc — ten assembled regional cubes plus two Nile subset cubes. Region names: Nile, Morocco, Sahel. Bboxes in docs/architecture/scope.v2.json.
- regional/<product>/<region>/<YYYY-MM>.nc4 — all 2,880 individual monthly DAP4 subsets with source-granule lineage.
- validation_regional_report.json — verification of every monthly file and every cube: 2,880/2,880 files open and read cleanly, 288/288 months per set, grid shapes match the bbox windows, finite-data and value-range checks.
- expanded_v2/docs/ — GPM and MODIS collection metadata, ATBD/user-guide PDFs and RAG corpus additions for the two new variables.

Units and grids:

| Product | Variable | Units | Native grid | Notes |
|---|---|---|---|---|
| M2TMNXSLV 5.12.4 | T2M | K | 0.5 deg lat x 0.625 deg lon | Nile cube is a subset of the Egypt parent cube |
| GLDAS_NOAH025_M 2.1 | SoilMoi0_10cm_inst | kg m-2 | 0.25 deg | land-only cells; sea masked. Nile cube is a subset of the Egypt parent cube |
| GPM_3IMERGM 07 | precipitation (+ quality index, random error) | mm/hr | 0.1 deg | monthly mean rate; mm/month = value x hours-in-month |
| MOD13C2 061 | NDVI (+ VI_Quality, pixel_reliability) | 1 | 0.05 deg CMG | real NDVI in [-0.2, 1.0]; fill -> NaN; QA fields kept raw |

All cubes use dims (time, lat, lon) with ascending lat/lon. Missing fractions per cube are in validation_regional_report.json; ocean and land-only model masks are expected, not errors.

## Role 01 artifacts (data ownership)

- `preprocess.py` — the only supported entry point for analysis code: `load_cube(product, window)`, `apply_qa(ds, product, mode)`, `regional_series(ds, product)`. `python preprocess.py --all` regenerates every artifact below.
- `qa_policy.json` — QA rules per product with the observed distributions that justify them. Key decisions: IMERG quality index is reported, never used as an exclusion filter (observed medians 5-7 on a 0-100 scale); MODIS uses MODLAND QA bits with default and strict modes.
- `coverage_report.json` — per cube: months, valid fraction, per-month min/median/max, all-missing and partial cells, value range, SHA-256.
- `regional_lineage.json` — 3,456 entries (4 products x 3 windows x 288 months) with SHA-256, byte size and source granule id per monthly file.
- `study_windows.geojson` — the three windows with bbox, native grid per product, period and limitations.
- `docs/roles/MEMBER_1.md` — the role's deliverable table, decisions and handoffs.

## Role 02 artifacts (statistics)

- `analysis/trend.py` — the single implementation for evidence cards **and** spatial maps: seasonal Mann-Kendall with Hamed-Rao correction, Theil-Sen slope on anomalies, block-residual bootstrap interval, BH-FDR for maps, period sensitivity.
- `analysis/method_config.json` — frozen `method_revision m2-1.0.0`: alpha, coverage rules, block length, seed, replicate count, FDR family, Spin It window set.
- `analysis/test_trend.py` — 9 synthetic checks (known slope, null, seasonality, AR(1), missingness, insufficient data, FDR, map, sensitivity). Run it before trusting any number.
- `analysis/reference_comparison.py` / `.json` — agreement with scipy, pyMannKendall and NASA POWER.
- `analysis/evidence_cards.json` — 12 cards: slope, interval, p, coverage, diagnostics, Spin It.
- `analysis/spatial_trends/*.npz` + `spatial_summary.json` — per-cell slope, p, FDR decision, valid months, dependence factor on the native grid.
- `analysis/INTERPRETATION.md` — the reviewed wording for Members 3, 4, 5 and 6.

```bash
cd data/nasa/analysis
python test_trend.py            # 9/9 must pass
python trend.py --all-cards     # regenerate cards
python trend.py --spatial       # regenerate maps
```

## Scope limits
The current numeric scope is four variables across three rectangles for 2001-2024, plus the two parent Egypt cubes. Rainfall and NDVI are included. NO2, global coverage, neighborhood-level and administrative-boundary datasets are outside this pack. Land-only model output has masked cells; use the regional validation report and the Morocco correction note. Spatial coverage is limited to native grid-cell centres inside the rectangles. Source model/reanalysis errors remain; ingestion checks do not prove physical truth.

The RAG corpus is a bounded set of official product and software documents, not an exhaustive scientific literature review. Product versions and source URLs are recorded; verify passage applicability because some guides cover multiple versions. The starter retrieval tests are historical and do not certify the expanded corpus. Statistical outputs (anomalies, slopes, uncertainty, significance, FDR, period-sensitivity matrices, evidence receipts) are computed later from these actual cubes. They are not downloaded facts, and no statistical or causal conclusions have been fabricated here. RAG answer quality remains to be evaluated with your chosen model.

Do not read the original rag/README.md or legacy runtime catalog as the final expanded availability state. Use this README, the actual cubes and `docs/architecture/scope.v2.json`. Its `source_variable` preserves the provider field, while `cube_variable` identifies the processed field (notably `NDVI`); `cube_units` records the units checked against the file. The source measurements are unchanged by this metadata clarification. The current statistics plan is `packages/science/PLAN.md` at the repository root.

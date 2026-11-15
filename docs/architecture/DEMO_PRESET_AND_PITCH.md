# Demo Preset and Judging Pitch

This demo preset is intentionally grounded in the verified 2001-01 to 2024-12 regional cubes in `data/nasa/measurements/`. It uses real values computed from the monthly regional averages over valid cells in each product and does not claim a validated significance result. The purpose is to demonstrate the Role 06 flow: select -> evidence -> sensitivity -> spatial contrast -> receipt.

## 1) Verified, reproducible Demo Preset

### Preset configuration

```yaml
preset_id: nile_2001_2024_demo
region_id: Nile
region_label: "Nile corridor [29,24,33,32]"
period:
  start_month: "2001-01"
  end_month: "2024-12"
variables:
  - T2M
  - SoilMoi0_10cm_inst
  - NDVI
method_revision: "not_released_for_significance"
notes:
  - "Uses the verified NetCDF regional cubes only."
  - "No fabricated trend claims. Results are descriptive and subject to the architecture's scientific caveats."
  - "NDVI is greenness, not crop yield or plant health in a causal sense."
  - "Inconclusive results are valid outputs."
```

### Source files used

- `data/nasa/measurements/M2TMNXSLV_Nile_2001_2024.nc`
- `data/nasa/measurements/GLDAS_NOAH025_M_Nile_2001_2024.nc`
- `data/nasa/measurements/MOD13C2_Nile_2001_2024.nc`

### Verified regional summary values

All values below are the monthly regional mean over valid cells for each product, from the 2001-01 to 2024-12 slice.

#### Nile T2M (MERRA-2, Kelvin)

- mean: 295.310642 K
- min: 283.757462 K
- max: 304.859036 K
- first month (2001-01): 286.249996 K
- last month (2024-12): 287.417930 K
- first-to-last change: +1.167934 K
- simple linear slope over full period: +0.003373 K per month

Equivalent to roughly 22.2 C on average for the 2001-2024 Nile window; this is descriptive only, not a significance claim.

#### Nile soil moisture (GLDAS, kg m-2)

- mean: 9.885705 kg m-2
- min: 7.548612 kg m-2
- max: 16.604539 kg m-2
- first month (2001-01): 13.527400 kg m-2
- last month (2024-12): 11.762371 kg m-2
- first-to-last change: -1.765030 kg m-2
- simple linear slope over full period: +0.000413 kg m-2 per month

This is a descriptive moisture decrease over the 24-year series; the architecture explicitly requires method-review before claims are labeled as significant.

#### Nile NDVI (MOD13C2)

- mean: 0.156066
- min: 0.132323
- max: 0.178320
- first month (2001-01): 0.169982
- last month (2024-12): 0.162668
- first-to-last change: -0.007314
- simple linear slope over full period: +0.000012 per month

NDVI is a greenness indicator, not crop yield or a direct measure of plant health. This is a summary of the monthly regional average, not a claim of a causal trend.

### Optional spatial contrast for the live demo

The architecture supports geographic sensitivity checks. The same calculation on the other two windows produces the following real first-to-last differences in the same period:

- Morocco T2M: +2.130444 K
- Morocco soil moisture: -8.625129 kg m-2
- Morocco NDVI: -0.051993
- Sahel T2M: -0.713278 K
- Sahel soil moisture: +0.389531 kg m-2
- Sahel NDVI: +0.044698

These comparisons are suitable for a sensitivity panel, but they remain descriptive and should not be framed as independent discovery claims without method review.

## 2) 75-second judging script (exact 5-step flow)

Use the following script in the demo flow. It follows the required sequence exactly: `select -> evidence -> sensitivity -> spatial contrast -> receipt`.

### Step 1: Select (15 seconds)

"We begin with the Nile corridor, a fixed study window defined as the Nile region in the project scope. We select the period from January 2001 through December 2024 and open the native-grid evidence for T2M and soil moisture, with NDVI as the vegetation lens."

### Step 2: Evidence (20 seconds)

"The verified cubes show a 2001-2024 Nile monthly mean temperature of 295.31 K, with a first month of 286.25 K and a last month of 287.42 K. The soil moisture series averages 9.89 kg m-2, starting at 13.53 and ending at 11.76. The NDVI average is 0.156, with a first value of 0.170 and a last value of 0.163. These are descriptive values from the real cubes, not a claim that the trend is statistically significant."

### Step 3: Sensitivity (15 seconds)

"We then test the same record for sensitivity to period and interpretation. The architecture explicitly treats inconclusive results as valid outputs. This matters because NDVI is only a greenness indicator and not a direct measurement of crop yield or plant health. We also avoid converting missing cells into zeros; the product masks remain in place."

### Step 4: Spatial contrast (15 seconds)

"To compare the local signal with other study windows, we show the same time-series logic for Morocco and Sahel. In the same 2001-2024 period, Morocco shows a stronger soil-moisture decline and a larger NDVI drop, while Sahel shows a smaller temperature change and a more stable soil-moisture signal. This is a comparison of regional context, not a proof of a causal mechanism."

### Step 5: Receipt (10 seconds)

"Finally, we export the receipt and CSV. The system preserves the request hash, data revisions, QA policy, mask logic, method revision, and source provenance. The offline fallback path is also ready: the demo can still show cached boundaries and evidence even when network or LLM access is unavailable."

## 3) Scientific caveats to keep in the live judging flow

- The architecture requires method review before significance labels, p-values, or confidence claims are shown.
- NDVI is a greenness indicator only; it is not crop yield and not a direct measure of plant health.
- Missing or masked cells are not zeros. The operational QA policy is applied before aggregation.
- Regional comparison is not a causal explanation. Shared model inputs can make products dependent.
- Inconclusive patterns are valid outputs and should be shown without over-claiming.
- The demo path is designed to be offline-safe and to export receipt metadata for replay and verification.

## 4) Demo-ready narrative summary

The Nile corridor remains a strong real-data demonstration because it combines a stable T2M monthly series, a land-surface soil moisture series, and a vegetation index series from the same period. The actual data show changes in the full-period monthly mean, but the project architecture is clear: trend evidence must be reviewed before it is labeled as significant. The real value of this demo is not a single conclusion; it is the reproducible workflow from region selection to evidence review, sensitivity testing, spatial comparison, and receipt export.

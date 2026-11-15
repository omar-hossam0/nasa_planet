# Reviewed interpretation text (Member 2 → Members 3, 4, 5, 6)

Method revision: **m2-1.0.0**. Every number below is produced by
`trend.py`; nothing in this file may be recomputed in prose, in the browser or
by a language model.

## 1. What a p-value means here (and what it does not)

Correct: *"The seasonal Mann-Kendall test gives p = 0.005, below the frozen
threshold of 0.05. Under the no-trend null, data at least this extreme would be
unlikely; we treat this as evidence against the null."*

Wrong, and banned from the UI, the RAG answers and the video script:

- "95% chance the trend is real" — a p-value is not a probability of a
  hypothesis.
- "p = 0.03 means a 3% chance it is random" — same error in another form.
- "Not significant, therefore no change" — absence of evidence is not evidence
  of absence; the effect size is still shown.
- "The trend is caused by X" — a trend is an association in time, never a
  causal claim.

Reference for this wording: Wasserstein & Lazar, *The ASA Statement on
p-Values* (2016).

## 2. What the interval means

`ci_low`/`ci_high` are a **95% percentile block-residual bootstrap interval for
the Theil-Sen slope in units per year**. Block length 12 months, 2,000
replicates, seed 20261114.

- It is an interval for the **slope**, not for the data and not for the
  intercept. The intercept of a Sen fit is never reported as an interval.
- It accounts for serial dependence and seasonality through the block
  resampling design; it is not a guarantee for every dependence structure.

## 3. Significance is not importance

With 288 monthly values, small effects can be detected. In the Nile NDVI map,
3,660 of 11,583 eligible cells pass FDR while the median slope is about
-0.00006 per year. Both facts are true and must be shown together:

- the **significance** column says "detectable relative to noise";
- the **magnitude** column says "how large the change actually is".

Never colour a map by significance alone. Colour by slope, outline the FDR
cells, and state the FDR threshold and family size on the card.

## 4. Regional card and cell map can disagree — and that is not a bug

Aggregating cells reduces noise, so the regional series can be significant
while no single cell is (Morocco air temperature: regional slope +0.031 °C/yr,
p = 0.158, while 0 of 80 cells pass FDR). Explain it as:

> "The regional average is less noisy than any individual cell, so a small
> regional change can be detectable even when no single cell is. The map shows
> where the change is largest, not where it is proven."

The regional slope is **not** the average of cell slopes; it comes from the
area-weighted regional series (cos-latitude weights, policy
`coslat_area_weighted_mean_v1`).

## 5. Current headline results (reference period 2001-01 to 2024-12)

| Variable | Window | Slope / year | 95% interval | p (Hamed-Rao) | Label |
|---|---|---|---|---|---|
| Air temperature (K→°C) | Nile | +0.0309 °C | +0.0096 … +0.0528 | 0.0052 | trend detected |
| Air temperature | Morocco | +0.0311 °C | +0.0034 … +0.0582 | 0.158 | inconclusive |
| Air temperature | Sahel | −0.0133 °C | −0.0333 … +0.0067 | 0.210 | inconclusive |
| Soil moisture (kg m⁻²) | Nile | +0.0025 | −0.0067 … +0.0119 | 0.639 | inconclusive |
| Soil moisture | Morocco | −0.0679 | −0.1218 … −0.0181 | 0.104 | inconclusive |
| Soil moisture | Sahel | −0.0314 | −0.0529 … −0.0105 | 0.0008 | trend detected |
| Precipitation (mm/hr) | Nile | +0.00000 | ≈0 | 0.135 | inconclusive |
| Precipitation | Morocco | −0.00051 | −0.0009 … −0.0001 | 0.049 | trend detected (borderline) |
| Precipitation | Sahel | +0.00004 | ≈0 | 0.892 | inconclusive |
| NDVI | Nile | +0.00017 | +0.0001 … +0.0002 | 0.032 | trend detected (small) |
| NDVI | Morocco | −0.00047 | −0.0016 … +0.0006 | 0.660 | inconclusive |
| NDVI | Sahel | +0.00068 | +0.0004 … +0.0010 | 0.0039 | trend detected (small) |

Two rows deserve care in the demo:

- **Precipitation Morocco p = 0.049** sits on the threshold; say "borderline"
  and show the interval, do not call it a strong signal.
- **Morocco air temperature** has an interval that excludes zero but p = 0.158.
  Present it as inconclusive and explain that the two summaries disagree —
  this is honest, and it is exactly the kind of case the "Challenge my
  conclusion" button exists for.

## 6. Per-product sentences that are safe to use

- Air temperature: "MERRA-2 reanalysis estimate for the 0.5° × 0.625° grid
  cells in this window; not a station reading."
- Soil moisture: "GLDAS land-surface model output for the top 0–10 cm layer in
  kg/m². Not a percentage and not relative humidity; sea cells are missing."
- Precipitation: "IMERG monthly mean rate in mm/hr. For mm/month multiply by
  the hours in that month. The quality index is reported beside the value, not
  used to hide cells."
- NDVI: "A vegetation greenness index between −0.2 and 1.0. Not yield, not
  biomass, not crop area."

## 7. Spin It wording

The sign-agreement fraction is **descriptive**: "In 9 of the 11 pre-registered
windows the slope keeps the same sign as the full period." It is not a
probability, and the window set is frozen in `method_config.json` precisely so
a reversal cannot be manufactured after the fact.

## 8. Insufficient data

If a series or cell fails the frozen coverage rule (60 months, 80% valid), the
result is `state = insufficient_data` with null slope, null p-value and null
interval. Show that state as its own visual case. Never substitute zero, never
estimate anyway, and never describe missing cells as zero moisture or no rain.

## 9. What has been verified, and what has not

Verified (see `reference_comparison.json` and `test_trend.py`):

- Theil-Sen slope identical to `scipy.stats.theilslopes` (difference < 1e-9).
- Mann-Kendall S and p identical to `pyMannKendall` (difference ≤ 2.2e-16);
  seasonal test p identical.
- MERRA-2 Cairo cell trend +0.0268 °C/yr vs NASA POWER Cairo point
  +0.0269 °C/yr over the same 288 months.
- Nine synthetic checks: known slope, null series, seasonality, AR(1)
  dependence, missingness, insufficient data, FDR control, spatial map,
  period sensitivity.

Not verified:

- No Giovanni cross-check was performed; it needs an interactive session and
  would have to reconcile product, period, mask, grid and weighting.
- FDR behaviour under real spatial autocorrelation is not calibrated; the
  family is stated so the reader can judge it.
- These are ingestion-and-method checks, not a climate attribution study.

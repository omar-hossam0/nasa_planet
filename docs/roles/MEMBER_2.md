# Role 02 — Statistics and scientific validity

Status: **DELIVERED** (14 November 2026, 20:05 Egypt time)
Method revision: **m2-1.0.0** (frozen in `data/nasa/analysis/method_config.json`)

Mission from `docs/architecture/PLAN.md`: own aggregation, anomalies, slopes,
uncertainty, autocorrelation handling, spatial multiplicity and period
sensitivity. Maintain one implementation for maps and evidence cards. Freeze
`method_revision` and minimum-series rules before releasing inference.

## Deliverables

| Deliverable | Path | Status | Evidence |
|---|---|---|---|
| Analysis library | `data/nasa/analysis/trend.py` | DONE | one estimator used by cards **and** maps |
| Frozen method config | `data/nasa/analysis/method_config.json` | DONE | alpha, coverage rules, block length, seed, FDR family all fixed before results |
| Test suite | `data/nasa/analysis/test_trend.py` | DONE | **9/9 checks pass** |
| External reference comparison | `data/nasa/analysis/reference_comparison.py` + `.json` | DONE | scipy, pyMannKendall and NASA POWER agreement |
| Evidence cards | `data/nasa/analysis/evidence_cards.json` | DONE | 12 cards with slope, interval, p, coverage, sensitivity |
| Spatial trend maps | `data/nasa/analysis/spatial_trends/*.npz` + `spatial_summary.json` | DONE | 12 maps, per-cell slope + FDR decision |
| Reviewed interpretation text | `data/nasa/analysis/INTERPRETATION.md` | DONE | wording rules for M3, M4, M5, M6 |

## Frozen method decisions (short form)

- **Test:** seasonal Mann-Kendall (Hirsch & Slack 1984), two-sided, alpha 0.05.
  A strong annual cycle therefore cannot be read as a trend.
- **Slope:** Theil-Sen on seasonal anomalies, reported in units per year.
- **Aggregation:** cos-latitude area-weighted regional series; the regional
  slope is **not** the mean of cell slopes.
- **Dependence:** Hamed-Rao variance correction, lags up to 24, only
  significant autocorrelations used; applied to cards **and** maps.
- **Interval:** 95% percentile block-residual bootstrap, block 12 months,
  2,000 replicates, seed 20261114. Estimand = slope, never the intercept.
- **Multiplicity:** Benjamini-Hochberg, q = 0.10, family = all eligible cells
  in one variable × window.
- **Minimum series:** 60 months, 48 valid months, 80% valid, else
  `insufficient_data` with nulls.
- **Spin It:** 11 pre-registered windows; sign agreement is descriptive.

## Verification actually run

```
python test_trend.py            -> 9/9 checks passed
python reference_comparison.py  -> library agreement: PASS
python trend.py --all-cards     -> 12 cards
python trend.py --spatial       -> 12 maps
```

Test results (from the run):

| Check | Result |
|---|---|
| known slope 0.5/yr | recovered 0.4998 (err 0.0002) |
| white-noise null | p = 0.489, not labelled a trend |
| seasonality only | p = 0.394, slope −0.002 |
| seasonality + 0.1/yr trend | slope 0.0953, p = 0.0027 |
| AR(1) null, 40 series | false positives 11/40 uncorrected → **0/40 corrected** |
| 15% missing | slope 0.2929 vs 0.3 truth |
| 30% missing | `insufficient_data` (coverage rule enforced) |
| BH-FDR, 200 families | mean FDP 0.087 at q = 0.10, power 1.000 |
| spatial map | trend half median 0.199, null half 0.000 |
| period sensitivity | 11 windows, same-sign fraction 0.55 on a reversing series |

External agreement:

- Theil-Sen vs `scipy.stats.theilslopes`: difference < 1e-9.
- Mann-Kendall vs `pyMannKendall`: S identical, p difference ≤ 2.2e-16;
  seasonal p identical.
- MERRA-2 Cairo cell **+0.0268 °C/yr** vs NASA POWER Cairo point
  **+0.0269 °C/yr** over the same 288 months (difference 0.00009 °C/yr).

## Headline results

Nile air temperature +0.031 °C/yr (95% interval +0.0096…+0.0528, p = 0.005);
Sahel soil moisture −0.031 kg/m²/yr (p = 0.0008); Sahel NDVI +0.00068/yr
(p = 0.0039); Morocco precipitation −0.0005 mm/hr/yr (p = 0.049, borderline).
Full table with honest labels in `INTERPRETATION.md` §5.

## Handoffs

- **Member 3 (backend):** result fields are exactly those in
  `evidence_card()`; states are `succeeded` / `insufficient_data`. A receipt
  must carry `method_revision`, `qa_policy_mode`, aggregation policy,
  anomaly baseline, block/seed/replicates and the FDR family.
- **Member 4 (RAG):** use `INTERPRETATION.md` §1, §3, §6 verbatim in prompts;
  numeric claims must be copied from the card fields, never recomputed.
- **Member 5 (map):** `spatial_trends/*.npz` holds slope, p, FDR mask and valid
  month counts on the native grid. Colour by slope, outline FDR cells, print
  the threshold and family size.
- **Member 6 (integration):** `period_sensitivity` is ready for Spin It; the
  window set is frozen, so the UI must not invent new windows silently.

## Open items (stated, not hidden)

1. **No Giovanni cross-check.** It needs an interactive session and a
   product/period/mask/grid/weighting reconciliation. The POWER comparison
   covers the independent-data-path requirement for one location.
2. **FDR under real spatial autocorrelation is not calibrated.** BH assumes a
   valid family of tests; spatial dependence means the true FDR may differ from
   q. The family and threshold are printed on every map so the reader can judge.
3. **Cell-level Hamed-Rao uses the same 24-lag rule as the series**, but with
   fewer valid months per cell the effective sample is smaller; cells below the
   coverage rule are excluded rather than corrected.

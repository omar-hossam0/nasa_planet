# Role 01 — Data acquisition and validity

Status: **DELIVERED** (14 November 2026, 19:20 Egypt time)

Mission from `docs/architecture/PLAN.md`: own product adapters, all twelve
cubes, QA policies, study-window geometry and source lineage. Reuse verified
Egypt data. Verify variable identity, scale, units and missing masks from
actual files — not from product pages.

## Deliverables

| Deliverable | Path | Status | Verification evidence |
|---|---|---|---|
| Source manifest | `data/nasa/manifests/{M2TMNXSLV,GLDAS_NOAH025_M,GPM_3IMERGM,MOD13C2}.json` | DONE | 288 granules each, 2001-01..2024-12, unique months |
| Study windows geometry | `data/nasa/study_windows.geojson` | DONE | 3 features, closed rings, bbox + native grid per product |
| Product preprocessing modules | `data/nasa/preprocess.py` | DONE | imports clean, `--all` regenerates every artifact below |
| QA policy | `data/nasa/qa_policy.json` | DONE | thresholds derived from observed QA distributions (see below) |
| Data revisions and hashes | `data/nasa/regional_lineage.json` | DONE | 3,456 entries (4 x 3 x 288), SHA-256 per monthly file, 0 missing |
| Coverage reports | `data/nasa/coverage_report.json` | DONE | 12 cubes x 288 months, per-month valid fractions, all-missing cells |
| Measurement-ready registry | `data/nasa/runtime_catalog.json` + `docs/architecture/scope.v2.json` | DONE | 14 catalog entries, all `analysis_ready: true`; 12/12 scope entries `verified_cube_ready` |
| Twelve cubes | `data/nasa/measurements/*_2001_2024.nc` | DONE | 288 months each, units and grids checked, value ranges physical |

## QA policy: the two decisions that matter

**1. IMERG quality index is NOT used as an exclusion filter.**
Observed in our own cubes: quality index min 0–1, median 5–7, max 20–36
(documented scale is 0–100, higher is better). Any fixed cut such as 50 or 80
would delete 100% of the data. The index and `randomError` are reported next
to every precipitation number for weighting and caveats only.

**2. MODIS masking follows MODLAND QA bits, with two modes.**
Default mode accepts bits 0–1 and `pixel_reliability` 0–1; strict mode accepts
bit 0 and reliability 0 only. Measured effect on NDVI validity:

| Window | passes default | passes strict |
|---|---|---|
| Nile | 0.906 | 0.886 |
| Morocco | 0.725 | 0.705 |
| Sahel | 0.999 | 0.946 |

Bits 2–3 (pixel not produced) are already NaN in the cubes, not zeros.
Morocco's 27% loss is the Atlantic inside the rectangle — expected, not an
error.

## How to use

```bash
cd data/nasa
python preprocess.py --all                        # regenerate all artifacts
python preprocess.py --series M2TMNXSLV nile_corridor
```

```python
import preprocess as pp
with pp.load_cube("MOD13C2", "nile_corridor") as ds:
    clean = pp.apply_qa(ds, "MOD13C2", mode="default")   # or "strict"
    series = pp.regional_series(clean, "MOD13C2")
```

`load_cube` and `apply_qa` are the only supported entry points for analysis
code. Do not read the raw `.nc` files with ad-hoc slicing; the QA policy and
the region registry live in this module.

## Handoffs

- **Member 2 (statistics):** cubes + `regional_series()` + `qa_policy.json`.
  Region slopes must come from the aggregated series, never from a single
  cell. Slopes in K and °C are numerically identical.
- **Member 3 (backend):** `runtime_catalog.json` is the availability source
  for `/v1/catalog`. Nothing outside it may be offered to a user.
- **Member 4 (RAG):** `manifests/` + `expanded_v2/docs/` are the product and
  version evidence for citations.
- **Member 5 (map):** `study_windows.geojson` carries the bbox, native grid
  and limitations per window. Rectangles include sea; do not imply
  neighbourhood precision.

## Sanity checks actually run

- Seasonal climatology Nile: 12.6 °C (Jan) to 30.0 °C (Aug).
- Seasonal climatology Sahel: pre-monsoon peak 34.2 °C (May), monsoon dip
  28.0 °C (Aug) — the expected Sahel signature.
- Seasonal climatology Morocco: 11.7 °C (Jan) to 26.3 °C (Aug).
- Cairo cell (30.0 N, 31.25 E): 12.4 °C Jan 2001, 29.6 °C Jul 2010 — matches
  the NASA POWER Cairo reference sample.

These are ingestion and plausibility checks, not climate conclusions.

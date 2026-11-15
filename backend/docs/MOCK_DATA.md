# Mock Data Reference

Everything here is **synthetic demonstration data**. Nothing is a NASA observation and
nothing is scientifically validated.

---

## 1. Where the fixtures live

| Module | Contents |
|---|---|
| `app/mocks/catalog.py` | Variable + region registry snapshot, aliases, dataset revisions |
| `app/mocks/analyses.py` | Series profiles, deterministic series generator, trend estimator |
| `app/mocks/spatial.py` | 3x3 grid builder, cell factors, GeoJSON polygons |
| `app/mocks/ai.py` | Keyword recommendation rules, EN/AR explanation templates |

Adapters (`app/adapters/mock_*.py`) are thin wrappers so services depend on protocols,
not on these modules.

---

## 2. Catalog snapshot

Derived from two repository files:

- `docs/architecture/scope.v2.json` — variable × region entries, bboxes, products,
  versions, coverage, readiness flags.
- `data/nasa/runtime_catalog.json` — legacy registry with units and native grid sizes.

| variable_id | Product | Version | Source variable | Unit | Units verified |
|---|---|---|---|---|---|
| `air_temperature` | M2TMNXSLV | 5.12.4 | T2M | K | yes |
| `soil_moisture` | GLDAS_NOAH025_M | 2.1 | SoilMoi0_10cm_inst | kg m-2 | yes |
| `precipitation` | GPM_3IMERGM | 07 | precipitation | mm day-1 | **no** |
| `vegetation_greenness` | MOD13C2 | 061 | CMG_0_05_Deg_Monthly_NDVI | 1 (unitless index) | **no** |

"Units verified" means a registry file in this repository asserts the unit. The two
`no` rows take their unit from product documentation that is not mirrored in the
repository, so the API flags them (`units_verified: false`, plus a `UNIT_UNVERIFIED`
warning) instead of presenting them as verified.

| region_id | Bbox `[W,S,E,N]` | Aliases |
|---|---|---|
| `nile_corridor` | `[29, 24, 33, 32]` | `egypt`, `nile` |
| `morocco_comparison` | `[-10, 30, -5, 35]` | `morocco` |
| `sahel_comparison` | `[-5, 12, 5, 17]` | `sahel` |

All entries declare coverage `2001-01 .. 2024-12`, `measurement_ready: true`,
`method_ready: false`, `app_available: false`.

Variable aliases: `T2M`→`air_temperature`, `SoilMoi0_10cm_inst`→`soil_moisture`,
`ndvi`→`vegetation_greenness`, `rain`/`rainfall`→`precipitation`.

> Regenerate `app/mocks/catalog.py` whenever the data team publishes a new
> `scope.v2.json`. It is a copy, not a runtime read, so the backend stays self-contained.

---

## 3. Series generation

`build_series()` produces one value per month:

```text
value = baseline
      + seasonal_amplitude * sin(2π (calendar_month - phase) / 12)
      + trend_per_year * trend_scale * years_elapsed
      + noise_amplitude * u(seed, index)
```

`u(seed, index)` is a deterministic pseudo-random value in `[-1, 1]` derived from
`sha256(seed:index)` — no `random`, no RNG state, identical on every machine.

| Variable | Baseline | Seasonal amplitude | Trend / year | Noise | Decimals |
|---|---|---|---|---|---|
| `air_temperature` | 296.0 K | 6.2 | +0.035 | 0.55 | 2 |
| `soil_moisture` | 8.4 kg m-2 | 2.6 | −0.018 | 0.35 | 3 |
| `precipitation` | 1.05 mm day-1 | 0.62 | +0.0021 | 0.14 | 3 |
| `vegetation_greenness` | 0.235 | 0.062 | +0.00062 | 0.011 | 4 |

Seed: `sha256(variable_id, start_month, end_month, offset_seed)`, where `offset_seed`
is `"<result_id>:<variable>:region"` for the regional series and
`"<result_id>:<cell_id>"` for a cell.

---

## 4. Trend estimator — and a bug it fixed

**Estimator:** ordinary least squares on **annual means of complete calendar years**,
producing a slope per year.

The first implementation regressed monthly values directly on time. That is wrong here:
a seasonal sine over calendar months is *not* orthogonal to a linear trend when the
sample spans a whole number of years, so the seasonal cycle leaked into the slope and
inflated a configured `+0.035 K yr-1` to `+0.072 K yr-1` (roughly 2×). Averaging
complete calendar years removes the seasonal term exactly, because each year contains
all twelve months once.

Consequences that are visible in the API:

- `n_years` reports how many complete years were used.
- A period shorter than three complete years yields `direction: "insufficient_data"` and
  `slope_per_year: null` — a two-year window cannot support a trend claim.
- `r_squared` refers to the fit on annual means, not on raw monthly values.

**Direction thresholds:** a slope is only called `increasing` / `decreasing` when
`|slope| > 10%` of the configured trend for that variable (e.g. 0.0035 K yr-1 for
temperature). Below that it is `inconclusive`. Without a significance test there is no
honest way to label a near-zero slope.

**What is deliberately not produced:** `p_value` is always `null`, `inference_status` is
always `not_computed`, and no confidence interval is reported. `r_squared` is a
goodness-of-fit number, not a significance test.

---

## 5. Spatial grid

- Fixed 3 columns × 3 rows over the analysis bbox, labelled `3x3_regular_lonlat`.
- Cell ids `cell_01 … cell_09`, row-major from the south-west corner.
- Each cell has a closed GeoJSON `Polygon` ring (5 positions), a `bbox`, and a centroid.
- Each cell's trend comes from its **own** generated series, so `/spatial` and
  `/cells/{id}` can never disagree.
- Cell divergence factor: deterministic value in `[-1.5, 1.0]` applied as
  `trend_scale = 1 + factor`. Because the range crosses −1.0, some cells flip the sign
  of the regional trend — the "what the average hides" case the product exists to show.
- `cell_09` is intentionally missing: every monthly value is `null`,
  `missing_data: true`, `trend_value: null`, `direction: "insufficient_data"`. Clients
  must render it as missing, never as zero.
- Cells are **not** an area-weighted decomposition of the regional series. The result
  carries a `REGIONAL_AVERAGE_HIDES_VARIATION` warning saying so.

---

## 6. Identifiers

| Artefact | Pattern | Derived from |
|---|---|---|
| Job | `job_mock_<8 hex>` | first 8 chars of the analysis cache key |
| Result | `result_mock_<8 hex>` | same cache key |
| Receipt | `receipt_mock_<8 hex>` | same cache key |
| Spin It | `spin_mock_<8 hex>` | sha256 of result id + window bounds |
| Comparison | `cmp_mock_<8 hex>` | sha256 of result id + cell ids |
| Explanation | `expl_mock_<8 hex>` | sha256 of result id + language |
| Cell | `cell_01 … cell_09` | grid position |
| Spin window | `window_01 … window_NN` | sweep order |

Because the analysis identifiers come from the request hash, the same request always
produces the same ids — across restarts and across machines.

---

## 7. Storage and lifetime

- `InMemoryJobRepository`, `InMemoryResultRepository`, `InMemoryReceiptRepository`,
  `InMemorySpinRepository`, `InMemoryAnalysisCacheRepository` — each a thread-safe dict.
- **Restarting the server deletes everything.** No job, result, receipt or spin survives.
- State is **per process**. Running uvicorn with `--workers 2` gives two disjoint worlds;
  a job created on worker A is invisible on worker B.
- Nothing is evicted, so memory grows with the number of distinct analyses.
- No database, no SQLite, no Redis, no Celery — intentional for this milestone.

The analysis cache is also in memory: a repeated identical request inside one process
returns the existing job with `cached: true` and HTTP 200.

---

## 8. Recommendations and explanations

- Keyword rules only (`provider: "mock_rules"`). Arabic is normalised (diacritics and
  tatweel stripped, alef/ya variants unified) before matching, on both the question and
  the keywords.
- Bare `moisture` / `humidity` / `رطوبة` returns `clarification_required`, because the
  catalog has soil moisture but no atmospheric humidity.
- Unmatched questions return `unsupported`; the message lists the supported variables.
- `references` is always `[]` in both recommendations and explanations. Nothing is
  retrieved, so nothing is cited. This is deliberate: an invented citation is worse than
  none.
- Explanations are templates filled from fields already stored in the result
  (`display_name`, region, period, slope, unit, cell counts). No new number is created.

---

## 9. How to change the demo data

| Want to change | Edit |
|---|---|
| Add a variable or region | `app/mocks/catalog.py` (`VARIABLES`, `REGIONS`) |
| Change trend/seasonality/noise | `app/mocks/analyses.py` (`PROFILES`) |
| Change grid size or missing cell | `app/mocks/spatial.py` (`GRID_ROWS`, `GRID_COLS`, `MISSING_CELL_INDEX`) |
| Change recommendation keywords | `app/mocks/ai.py` (`RULES`) |
| Change explanation wording | `app/mocks/ai.py` (`build_explanation`) |

Tests assert structure and invariants rather than exact fixture values, so most changes
require no test edits — except `tests/test_spatial.py`, which assumes a 3x3 grid and
`cell_09` as the missing cell.

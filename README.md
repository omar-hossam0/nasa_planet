# NASA Planet - Trend Detective

Team reference for **What the Average Hides**: investigate Earth-system trends, test sensitivity to period and location, and export reproducible evidence.

## Start here

- [Team entry point](docs/START_HERE.md)
- [Architecture, scope, six-person responsibilities and delivery plan](docs/architecture/PLAN.md)
- [Implementation specification: components, API, jobs, science, RAG and verification](docs/architecture/IMPLEMENTATION.md)
- [Machine-readable target scope](docs/architecture/scope.v2.json)
- [Data guide](data/nasa/README.md)
- [Verified measurements and validation report](data/nasa/validation_report.json)

## Delivered versus planned

**Delivered in this working branch:** temperature (MERRA-2), precipitation
(GPM IMERG), soil moisture (GLDAS) and vegetation greenness (MODIS) across
Nile, Morocco and Sahel study windows, monthly 2001–2024. The
[coverage report](data/nasa/coverage_report.json) and
[regional validation](data/nasa/validation_regional_report.json) document the
measurements and QA. The backend, statistics pipeline, citations, React
product and [release checks](docs/acceptance_report.json) are present. The
production experience still needs deployment and review on real devices.

These application commits are local on `feature/react-product-ui`; the remote
`main` branch remains the data-only history chosen earlier.

## Repository map

```text
docs/START_HERE.md             Reading order and current delivery status
docs/architecture/            Plan, implementation contracts and target scope
data/nasa/measurements/       Actual regional source subsets and combined cubes
data/nasa/frontend/           Browser-friendly values, coordinates and units
data/nasa/rag/                Cited corpus, retrieval baseline and AI contract
data/nasa/docs/               NASA product guides
data/nasa/methods/            Software-method documentation
data/nasa/manifests/          NASA granule inventories
data/nasa/source_lineage.json Per-month source IDs and file hashes
```

## Quick start

For dependency-free retrieval:

```bash
python data/nasa/rag/retrieve.py "soil moisture"
```

For numerical work, install the pinned dependencies in a virtual environment:

```bash
python -m venv .venv
# Activate the environment for your shell, then:
python -m pip install -r data/nasa/requirements.txt
```

```python
import xarray as xr

ds = xr.open_dataset("data/nasa/measurements/M2TMNXSLV_Egypt_2001_2024.nc")
temperature_c = ds["T2M"] - 273.15
```

Reading the bundled measurements does not require Earthdata credentials. Re-downloading does; use only the local interactive login. Never commit credentials or tokens.

## Source attribution and limitations

Source URLs, product versions and hashes are preserved in the data bundle and architecture. Temperature is reanalysis and soil moisture is model output; neither is a direct station observation. The rectangle includes adjacent areas and sea and is not a national boundary mask. Different products retain different native grids. Missing values are not zeros.

Official source documents retain their original attribution and applicable terms; this repository does not assign a new blanket license to third-party content. No statistical or causal conclusions are implied by the downloaded data.

## Run the service locally

```bash
cd backend
python -m pip install -r requirements.txt -r ../data/nasa/requirements.txt
python run.py            # product: http://127.0.0.1:8000/  · API docs: /docs
python -m pytest tests/test_api.py -q
```

API contract for the frontend and AI roles: `backend/CONTRACTS.md`.
Role-by-role deliverables and handoffs: `docs/roles/`.

## Demo and offline fallback

The public entry page is `/` (redirects to the React product at `/product/`).
Its Launch explorer action opens the new React analysis workspace. The former
static UI remains at `/app/` for compatibility. See [frontend/README.md](frontend/README.md)
for build and offline instructions. Landing illustrations are conceptual;
analysis numbers come from the verified backend or the precomputed snapshot.

```bash
cd backend && python run.py        # product: http://127.0.0.1:8000/
python warm_cache.py               # pre-warm the demo presets
python tools/acceptance_check.py   # 15 release checks -> docs/acceptance_report.json
python tools/export_offline.py     # rebuild dist/offline (12 analyses, ~2.7 MB)
```

One URL reproduces the stage state:
`/app/?lang=ar&region=nile_corridor&variable=air_temperature&autorun=1`

If the network fails, run `dist/product/START_OFFLINE.cmd` (Node.js required)
for the React product and precomputed results. The previous static offline
snapshot remains at `dist/offline/index.html`. The 90-second script is in
`docs/DEMO_SCRIPT.md`; per-role handoffs are in `docs/roles/`.

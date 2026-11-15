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

**Delivered data:** all twelve regional cubes: temperature (MERRA-2), precipitation (GPM IMERG), soil moisture (GLDAS) and vegetation greenness (MODIS) across the Nile, Morocco and Sahel study rectangles, monthly January 2001 through December 2024. The two original Egypt cubes are retained as parent/reference assets. The expanded pack includes 2,880 downloaded regional monthly subsets; the original pack includes 576 monthly subsets.

**Current statistics work:** [data-aligned implementation plan](packages/science/PLAN.md) and [progress](packages/science/PROGRESS.md). Source/processed field identities are explicit in `docs/architecture/scope.v2.json`. Core input preparation precedes inference validation and service integration. The main-derived checkout has no full application; implementations on other branches require reconciliation and review before reuse.

Data-ingestion readiness is not scientific-method or application readiness. Follow the separate readiness gates in the architecture.

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

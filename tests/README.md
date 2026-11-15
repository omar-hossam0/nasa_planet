# Role 06 test suite

This directory contains verification scripts for the Role 06 end-to-end integration and release checks described in the architecture documents.

## Files

- `qa_audit_cubes.py` - base cube integrity audit for the 12 regional NetCDF data files
- `verify_coordinate_order_and_grid_shapes.py` - grid steps, axis ordering, and study-window bounding checks
- `verify_product_qa_masks_and_fill_rules.py` - MODIS and GPM QA checks plus missing/sea-cell fill encoding
- `verify_units_and_scale_decoding.py` - units and scale decoding checks for temperature, soil moisture, precipitation and NDVI
- `verify_api_contracts.py` - catalog, analysis request, hash idempotency, and receipt contract checks
- `verify_rag_grounded_answers.py` - explanation schema, citation validation, numeric consistency, and prompt-injection checks
- `verify_release_gate.py` - release gate checks for determinism, export schema, offline readiness, source credits and secret scanning

## Running the suite

From the repository root, run the offline data-layer checks first:

```powershell
.\.venv\Scripts\python.exe tests/qa_audit_cubes.py
.\.venv\Scripts\python.exe tests/verify_coordinate_order_and_grid_shapes.py
.\.venv\Scripts\python.exe tests/verify_product_qa_masks_and_fill_rules.py
.\.venv\Scripts\python.exe tests/verify_units_and_scale_decoding.py
```

Then, if you want to validate the Python files compile cleanly before running tests:

```powershell
.\.venv\Scripts\python.exe -m py_compile tests/*.py
```

To run live API checks against a started service, first start the backend and then set:

```powershell
$env:TREND_DETECTIVE_API_BASE = "http://localhost:8000"
```

Then run the specific verification scripts:

```powershell
.\.venv\Scripts\python.exe tests/verify_api_contracts.py
.\.venv\Scripts\python.exe tests/verify_rag_grounded_answers.py
.\.venv\Scripts\python.exe tests/verify_release_gate.py
```

The suite is intentionally designed so the scripts do not require a running API server for compile validation. When no backend is available, they print a dry-run message instead of calling localhost.

## Expected verification order

1. Validate data bundle integrity.
2. Validate native grid geometry and coordinate ordering.
3. Validate product QA masks and fill rules.
4. Validate units and conversion logic.
5. Validate API contracts and request hashing.
6. Validate grounded explanations and citation resolution.
7. Validate release readiness and export determinism.

## Notes

- No credentials or secrets should be committed to this repository.
- All output exports and receipts should be reproducible and deterministic.
- API and RAG checks are meant for a running service, not for offline development without the backend.

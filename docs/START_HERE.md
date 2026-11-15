# Team reference: Trend Detective

Read in order:

1. [Architecture and six-person plan](architecture/PLAN.md).
2. [Implementation specification](architecture/IMPLEMENTATION.md).
3. [Machine-readable target scope](architecture/scope.v2.json).
4. [Verified existing data](../data/nasa/README.md).
5. [Data validation report](../data/nasa/validation_report.json).

All four variables across the three study windows are present for 2001-2024: **12 regional cubes**, each with 288 months. The original two Egypt cubes are also retained. GPM quality/error fields and MODIS QA/reliability fields are bundled. This is source availability, not scientific-method or application approval.

Use `docs/architecture/scope.v2.json` for the expanded input mapping (`source_variable`, `cube_variable`, `cube_units` and paths), and `data/nasa/validation_regional_report.json` for the source-delivery checks. `runtime_catalog.json` is the legacy two-variable Egypt registry. Do not use it to infer full application readiness.

No application files are implemented by this documentation/data delivery. The project plan governs future work; adapt proposed module paths to the repository's established structure.

For current numerical work, read [the statistics plan](../packages/science/PLAN.md),
[its progress tracker](../packages/science/PROGRESS.md), and the latest statistics
phase report. The earlier Phase 0 report is historical; its NDVI mapping issue is
resolved by an explicit processed-field contract. Backend schema review remains
an integration requirement, rather than a blocker for local input preparation.

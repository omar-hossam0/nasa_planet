# Science and RAG recheck — 15 November 2026

## Verdict

The displayed application is a synthetic demo, not an integrated real-science
pipeline. Previous browser checks established UI/API agreement, not scientific
correctness. The statistics adapter and result explanation adapter are still
`MockStatisticsAdapter` and `MockRAGAdapter` in `app/core/dependencies.py`.

The screenshot's `0.0359 K year-1` is a descriptive least-squares slope calculated
from a generated seasonal/noisy series. Its 3×3 map is also generated; the mock
regional series is not the weighted mean of these map cells. Its displayed
explanation is a deterministic template, not the separate Gemini question service.
The `100%` indicator counts valid monthly values, not measurement authenticity,
scientific confidence, or complete quality-approved spatial coverage.

## Independent numerical check

Source inspected: `data/nasa/measurements/M2TMNXSLV_Nile_2001_2024.nc`.
It contains 288 months, 17 latitude rows and 6 longitude columns (102 cells).

A read-only diagnostic supplied the missing `cube_variable=T2M` and `cube_units=K`
fields **in memory**, from `input_audit_current.json` and source-file metadata.
No installed contract, readiness flags, source measurements or scientific policy
were modified. It then ran the existing default strict preparation and annual
science estimator on the real file.

| Calculation | Annual slope, K/year |
| --- | ---: |
| Recomputed science, annual Theil–Sen, strict support | 0.025330383313493597 |
| Independent Python median of all 276 annual pairwise slopes | 0.025330383313493597 |
| Archived Phase 3 result for the same case | 0.025330383313493597 |
| User screenshot, synthetic annual-mean least squares | 0.0359 |

These are different data/method paths. The real diagnostic does not make the
displayed synthetic number a valid NASA measurement result. One reproduced case
does not certify every variable/region, inference, representativeness or release.
Diagnostic output: ignored `backend/var/science_recheck.json`.

## Current science blocker

The default `src.data_loader.input_entry()` reads
`docs/architecture/scope.v2.json`, whose current entries omit `cube_variable` and
`cube_units`. It fails with `Missing explicit input contract field: cube_variable`.
The newer audit and phase results describe an explicit contract that the installed
file currently does not satisfy. The root `scope.v2.json` also disagrees with the
architecture copy about readiness. Do not infer readiness from either flag alone.

After installing the declared source-reader and plotting dependencies, running
`python -m pytest packages/science/tests -q` reported:
**104 passed, 19 failed, 7 errors, 42 subtests passed**. Failures/errors report the
missing input-contract fields. Log: ignored
`backend/var/science-tests-recheck.txt`.

## RAG live checks

- English soil-moisture question: `mode=llm`, nonempty answer, four citations.
- Arabic NDVI question: initially generated English despite Arabic input. Added an
  explicit answer-language instruction and repeated the live call; it returned
  Arabic, `mode=llm`, four citations and no fallback.
- Returned citation IDs, quoted evidence and URLs matched the actual corpus in
  the checked replies. Source-pointer correctness does not prove every generated
  sentence or every possible question is correct.
- Football query: classified unsupported; no generated answer or citations.
- RAG documentation Q&A does not read stored analysis results. Successful Gemini
  Q&A therefore does not establish that science is connected to result explanations.

## Required integration work

Reconcile the explicit scientific input contract against source metadata and
rerun science tests. Implement real data/statistics adapters and native-grid
result mapping. Pass the stored, approved descriptive result into Role04's
conclusion renderer. Keep inferential statistics disabled until their scientific
release criteria pass. Continue labeling synthetic mode honestly in the interim.

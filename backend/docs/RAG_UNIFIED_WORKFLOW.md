# Unified question and result workflow

Current implementation/report: [retained bilingual audit](../../tools/rag_language_audit_20261115/REPORT.md).

`POST /v1/explanations/ask` accepts query, language, optional selected region and
start/end months. It returns existing documentation answer/evidence fields plus
`workflow`: state, reason_code, resolved region/variables, availability metadata,
and an executable `analysis_request` only when unambiguous and available. This
endpoint proposes a computation; it does not silently submit jobs. The UI lets
the user apply the proposal and run the standard analysis flow.

Explicit recognizable query regions override the selected region. Multiple
registered regions or variables request clarification. Dates in the question
override context dates; reversed/out-of-coverage periods cannot produce a ready
proposal. Alias discovery is curated and bounded, not a universal geographic NER.

Shared RAG contracts live in `packages/rag/result_contracts.py` and `judge.py`.
The statistics schema can carry typed `inference` separately from its descriptive
Sen slope. No method is registered as scientifically released. The current
assessment therefore returns inference unavailable; numerical tests of the
Judge use an injected synthetic-only registry. This does not enable NASA p-values.

Current result rendering is Role04 `render_assessment` -> shared
`result_templates.py`. The backend retains numerical consistency and review
rules. Legacy result entry points remain for compatibility; they are not a
scientific release mechanism for this app. Local read-only diagnostic reports do
not automatically certify new AOI/time selections.

The repository root is initialized on the backend package import path so shared
contracts are available consistently from root and backend working directories.
Restart the API after region aliases or contracts change.

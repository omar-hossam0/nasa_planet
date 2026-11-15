# Request-specific result assessment

POST `/v1/explanations` now includes `assessments[]`, one per real result variable,
alongside bilingual deterministic sections. Mock explanations retain their existing
sections and return an empty assessment array. There is no result-generation LLM.

`ResultAssessment` exposes result/variable identity, policy revision, descriptive
status, descriptive direction, inference availability, model-diagnostic status,
localized reason codes/severity/messages, and the numeric facts used by templates.
The frontend displays structured conclusions, reasons, separate factual sections
and expandable source links. Arabic negative values use directional isolation.

## Rules and evidence

- Reconcile the annual artifact, actual year labels, complete-year count, monthly
  valid count and stored Sen slope before allowing a descriptive direction.
- Describe the actual request period and support, not an assumed full-period result.
- Explain short records using complete annual values (five years is not 60
  independent annual observations). The current research review threshold is 20;
  reaching it does not establish validity or approval.
- Report limited retained native-cell area independently of temporal completeness.
  Zero retained support blocks interpretation; inconsistent support is flagged.
- Calculate leave-one-year-out Sen slopes using actual remaining year labels.
  Report sign sensitivity without calling it confidence or statistical significance.
- Explain Kelvin temperature changes and Celsius changes consistently; monthly
  Celsius means are a deterministic conversion from stored Kelvin means.
- Ignore any stray unreleased p-value. Neither an `approved` boolean alone nor
  a diagnostic audit elsewhere can authorize a significance claim.

Policy: `backend/config/assessment_policy.json`, loaded once per process. Restart
API/workers after changes. The 50% area review threshold and 20-year record review
threshold are configurable review cues, not NASA quality requirements. Numeric
science estimators, QA policies and source data were not changed by this feature.

## Deliberate scientific boundary

This is an interpretation/consistency assessment, not an automatic scientific
certification. Current inference status remains `not_available`. Model diagnostics
are explicitly `not_run_for_this_result`; the saved 12-case full-period audit is
not reused as if it covered an arbitrary custom AOI/time period. Running those
diagnostics or releasing a validated inferential method requires a separate
versioned contract and validation. The result card does not imply that such work
has occurred. Documentation Q&A retains its independent retrieval capability.

## Verification

- Active backend suite: 177 tests pass; legacy `tests/test_api.py` is excluded as
  documented because it targets a superseded contract.
- Tests cover all 12 real source pairs, short windows, Arabic/English numeric
  parity, inconsistent artifacts, ignored p-values, low/zero QA support, missing
  years, configuration, and sign changes in actual Nile precipitation data.
- TypeScript and Vite build pass (output directed to ignored backend/var).
- `python tools/audit_explanation_visuals.py` passes in real Chromium: structured
  result card, actual Sahel NDVI area warning, mobile layout, Arabic five-year
  warning, and absence of Gemini result controls. No provider calls are made.

Retained browser evidence: `backend/var/explanation-visuals/assessment-*.png` and
`report.json`. Prior statistical audit scripts/data remain retained.

# Stage 2 approval and Phase 3 authorization

Recorded: 15 November 2026. Branch: `codex/ml-statistics`.

The user explicitly instructed: “Begin Phase 3 according to PLAN.md after
recording approval of the Stage 2 checkpoint.” This records that approval to
advance from the completed Stage 2 checkpoints into descriptive estimator work.

Reviewed evidence remains available in:

- [Stage 2 implementation](PHASE_2_REPORT.md).
- [Sahel QA and coverage](SAHEL_NDVI_POLICY_CHECKPOINT.md).
- [Standard 95% monthly/annual review](SAHEL_NDVI_STANDARD95_REVIEW.md).

Approved scope: implement and validate Theil–Sen regional and cell slopes with
explicit elapsed-year axes, known-trend/missing/short-series checks and trusted
reference comparisons; report units, limitations and preparation sensitivity.
Stop at the Phase 3 checkpoint for review.

Conditions carried forward:

- Strict 100% remains the default; Standard 100% is a separate comparison.
- Standard 95% stays experimental. Incomplete cell-years stay missing and
  cannot become annual observations through averaging partial years.
- Preserve Stage 2 policy and data bytes. The historical `candidate_pending_owner_review`
  label inside the immutable policy file is not rewritten; this separate record
  documents authorization for the specified downstream work.
- No p-values, confidence intervals, significance classifications, inference
  release, application-readiness promotion or Phase 4 implementation is authorized.

This approval is not a default-policy change or a claim of measurement accuracy.

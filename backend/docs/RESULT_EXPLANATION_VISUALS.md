# Result explanations and interpretation visuals

Result explanations exclusively use deterministic Role04 bilingual templates over
stored science results. POST /v1/explanations accepts result_id and language only.
The optional result-generation service, frontend button and configuration have
been removed; requests containing style are rejected. Documentation questions at
/v1/explanations/ask retain their separate retrieval/Gemini capability.

P-values and confidence intervals remain unavailable because the evaluated
inferential methods failed scientific validation. Removing result generation does
not change the science estimator or authorize unvalidated inference.

## Visual interpretation

- Annual observations chart, with actual calendar years, a keyboard/touch year
  selector and an expandable annual-values table. It has no forecast line or
  confidence band. The vertical scale follows the observed data range.
- Histogram of existing native-cell annual slopes. Counts refer to computed cells,
  not confidence limits. Bins that touch zero have a neutral colour.
- Source-derived counts for positive/negative/zero/unavailable eligible cells.
  No direction is labeled statistically significant.
- Spatial QA-retention donut and a separate temporal completeness meter. For
  example, Sahel NDVI can have a complete monthly regional series while retaining
  only about 14.7% of the selected native-cell area.
- An expandable explanation beside the missing p-value/interval, showing the
  completed data/description steps and the withheld uncertainty step.

## Verification

Run the active backend suite and frontend TypeScript/build checks.
Run `python tools/audit_explanation_visuals.py` for the visualization browser audit;
it also asserts that the result-generation controls are absent. No live provider
option remains in this audit.

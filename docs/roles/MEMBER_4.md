# Role 04 — RAG and grounded explanations

Status: **DELIVERED** (14 November 2026, 20:40 Egypt time)
Schema version: **m4-1.0.0** · consumes method **m2-1.0.0** via API **m3-1.0.0**

Mission from `docs/architecture/PLAN.md`: own bilingual interpretation,
product/version-aware retrieval, citations, result-grounded explanations and
fallback. Extend the 315 source chunks with the new products and QA guides.
Distinguish official evidence from team-authored aliases, prompts and
evaluation cases.

## Deliverables

| Deliverable | Path | Status | Evidence |
|---|---|---|---|
| Versioned corpus | `ai/corpus/corpus.v1.jsonl` + `manifest.json` | DONE | **522 chunks**, version hash, per-source sha256 |
| GPM + MODIS coverage | same | DONE | GPM 141 chunks (ATBD V07, page-tagged), MODIS 63 (User Guide V6.1) |
| Retrieval adapter | `ai/retrieve.py` | DONE | BM25 + product filter + injection exclusion; returns chunk ids and pages |
| Strict explanation schema | `ai/validator.py` | DONE | `schema_version m4-1.0.0`, 9 required fields, 12 rejection codes |
| Answer validator | `ai/validator.py` | DONE | citations, numbers vs result fields, availability, wording, state |
| Deterministic fallback | `ai/explain.py` | DONE | no model, no key, no network; always valid |
| Evaluation harness + report | `ai/evaluate.py`, `ai/evaluation_report.json` | DONE | **19/19 cases pass** |
| API integration | `GET /v1/analyses/{job_id}/explanation` | DONE | wired into M3, 2 new backend tests |

## Corpus composition (was 315, now 522 chunks)

| Product | Chunks | Authority |
|---|---|---|
| MERRA-2 | 228 | official NASA |
| GLDAS | 58 | official NASA |
| **GPM IMERG V07** | **141** | official NASA (new) |
| **MODIS MOD13C2 V061** | **63** | official NASA (new) |
| Software method docs | 29 | official software docs (not NASA) |
| Project policy | 3 | project-authored, `citable_for_facts: false` |

`authority` and `citable_for_facts` keep team-authored notes (Arabic aliases,
QA policy, interpretation rules) visibly separate from NASA evidence.

## Required case families (from PLAN.md)

| Family | Case | Result |
|---|---|---|
| Unavailable regions | suggestion against an unavailable region is rejected | PASS |
| Air/surface ambiguity | limitation names land-surface temperature explicitly | PASS |
| NDVI limits | answer states NDVI is not yield/biomass | PASS |
| Units | soil moisture answer states kg/m2, not percent | PASS |
| False causality | "caused by global warming" rejected | PASS |
| Missing data | insufficient-data state, zero numbers, no slope | PASS |
| Malicious instructions in retrieved text | chunk excluded from retrieval; a citation to it rejected | PASS |

Extra adversarial cases: probability-of-trend claim, wrong number, invented
citation, unavailable variable suggestion, and four LLM-fallback modes
(bad numbers, causality, citation, injection).

## What the validator enforces

- every citation resolves to a chunk that was actually retrieved;
- every number matches a field of the verified result payload (rounded
  renderings allowed, invented numbers rejected);
- every suggested variable is measurement+method ready in that region;
- banned wording: probability-of-hypothesis, "proves", causal language,
  forecasts, NDVI-as-yield, missing-as-zero, followed injections;
- insufficient-data results may not carry numbers.

## Handoffs

- **Member 3:** endpoint already wired; `path` tells you whether the answer was
  deterministic or model-generated, and `validation.warnings` carries rejection
  reasons when a model answer was replaced.
- **Member 5:** use `explanation.answer` and `limitations[]` verbatim; the
  `citations[]` array has chunk id, title, page and source URL for the source
  panel. Arabic and English share the same numbers and source ids.
- **Member 6:** for the demo, prefer the deterministic path — it cannot fail
  and needs no key. If a provider is configured, keep the fallback visible.

## Open items

1. **No real provider call.** The LLM path is proven only with deterministic
   stubs; generated-answer quality remains untested until a key is available.
2. **Arabic retrieval is lexical**, with a small project-authored alias
   dictionary; not a semantic evaluation.
3. **No human usefulness rating.**
4. **Chunking is fixed 1400 characters** with page boundaries; semantic
   chunking is a later improvement, not a claim made here.

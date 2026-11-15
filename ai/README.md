# Explanation layer (Member 4)

Bilingual, source-grounded explanations for a finished analysis. Deterministic
by default; a language model is optional and never trusted without validation.

## Run

```bash
python ai/corpus_build.py     # rebuild the versioned corpus
python ai/evaluate.py         # 19 evaluation cases -> evaluation_report.json
python ai/retrieve.py "soil moisture units"
```

Through the API:

```bash
curl "http://127.0.0.1:8000/v1/analyses/<job_id>/explanation?language=ar"
```

## Pieces

| File | Role |
|---|---|
| `corpus_build.py` | builds `corpus/corpus.v1.jsonl` + `corpus/manifest.json` from NASA docs, PDFs and CMR metadata; labels team-authored notes separately; flags instruction-like text |
| `retrieve.py` | BM25 retrieval with product filters, Arabic alias expansion (project-authored), injection chunks excluded |
| `validator.py` | admission gate: citations, numbers, availability, wording, state consistency |
| `explain.py` | deterministic answer builder, optional LLM adapter, strict JSON schema |
| `evaluate.py` | required case families + adversarial cases, writes the report |

## Corpus

522 chunks in `corpus.v1.jsonl`, versioned by a hash of all chunk ids and texts.

| Product | Chunks | Sources |
|---|---|---|
| MERRA-2 (`M2TMNXSLV`) | 228 | README, specification, reprocessing notes, CMR metadata |
| GLDAS (`GLDAS_NOAH025_M`) | 58 | GLDAS guide, model description, CMR metadata |
| GPM IMERG (`GPM_3IMERGM`) | 141 | ATBD V07 (page-tagged), CMR metadata |
| MODIS (`MOD13C2`) | 63 | MOD13 User Guide V6.1 (page-tagged), CMR metadata |
| Software method docs | 29 | SciPy, statsmodels, pyMannKendall |
| Project policy | 3 | QA and method notes, `citable_for_facts: false` |

Two labels matter: `authority` (`official_nasa` vs `project_authored`) and
`citable_for_facts`. Project notes may be quoted as *our* policy, never as NASA
evidence.

## Validation rules (why an answer can be rejected)

| Rule | Rejection code |
|---|---|
| citation is not in the retrieved set | `CITATION_NOT_RETRIEVED` |
| a number does not match a field of the result | `NUMERIC_VALUE_MISMATCH`, `NUMERIC_FIELD_NOT_FOUND` |
| a number in the prose is not referenced | `UNREFERENCED_NUMBER` |
| suggested variable is not measurement+method ready | `SUGGESTION_UNAVAILABLE` |
| "95% chance the trend is real", "proves", "caused by", "will increase by" | `BANNED_PHRASING` |
| NDVI described as yield/biomass | `BANNED_PHRASING` (ndvi_overclaim) |
| missing data described as zero | `BANNED_PHRASING` (missing_as_zero) |
| instruction text from a passage followed | `BANNED_PHRASING` (injection_followed) |
| numbers supplied for an insufficient-data result | `NUMBERS_WITH_INSUFFICIENT_DATA` |

When the LLM path fails validation the deterministic answer is served instead,
and the response records `path: deterministic_fallback` with the rejection
reasons in `validation.warnings`.

## Evaluation result

`evaluation_report.json`: **19/19 cases pass** — corpus coverage, deterministic
validity, air-vs-surface wording, soil-moisture units, NDVI limits,
insufficient-data state, and rejection of: probability claims, causal claims,
wrong numbers, invented citations, unavailable suggestions, unavailable region,
retrieved-text injection, plus four LLM-fallback modes.

## Honest limits

- **No real LLM was called.** The LLM path is exercised with deterministic
  stubs; a provider key is required before claiming generated-answer quality.
- **Arabic retrieval is lexical** with a small project-authored alias
  dictionary — not a semantic-search evaluation.
- **No human usefulness rating** was performed.
- The corpus is bounded to the shipped documents; it is not a literature
  review, and it never establishes a trend by itself.

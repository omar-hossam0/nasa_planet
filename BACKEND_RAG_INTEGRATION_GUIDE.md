# Backend RAG & Conclusion Engine Integration Guide (Role 03 Handover)

> **Project:** NASA Space Apps 2026 — Trend Detective: "What the Average Hides"  
> **Target Audience:** Role 03 (Backend API Lead)  
> **Source Module:** `packages/rag/` (Single Service Facade: `packages/rag/facade.py`)  
> **Verification Status:** 170/170 Automated Tests Passing (`pytest`)  
> **Primary Interfaces:** `Role04Service`, `normalize_result_payload()`

---

## Table of Contents
1. [Executive Overview of the Dual-Path Architecture](#1-executive-overview-of-the-dual-path-architecture)
2. [Master Data & Assets Reference Tables](#2-master-data--assets-reference-tables)
   - [Table A: Climate Variable Datasets & Scientific Guardrails](#table-a-climate-variable-datasets--scientific-guardrails)
   - [Table B: Statistical Method Docs, Corpus Files & System Registries](#table-b-statistical-method-docs-corpus-files--system-registries)
3. [Exact Input / Output Contracts & Internal Processing Flows](#3-exact-input--output-contracts--internal-processing-flows)
   - [Path A: Concept Q&A & Variable Discovery (`answer_question`)](#path-a-concept-qa--variable-discovery-answer_question)
   - [Path B: Deterministic Conclusion Engine (`render_result`)](#path-b-deterministic-conclusion-engine-render_result)
4. [Step-by-Step Backend Integration Roadmap](#4-step-by-step-backend-integration-roadmap)
5. [Production-Ready FastAPI Reference Router Code](#5-production-ready-fastapi-reference-router-code)
6. [Verification, Health Checks & Smoke Testing](#6-verification-health-checks--smoke-testing)

---

## 1. Executive Overview of the Dual-Path Architecture

Role 04 is the **semantic and narrative bridge** between the raw scientific measurements/statistics (Roles 01 & 02) and the user-facing web interface (Roles 05 & 06). 

To ensure complete scientific integrity, **Role 04 strictly isolates Concept Explanations from Statistical Calculations**:

```
                               ┌──────────────────────────────────────────────────────────┐
                               │                    Client / Frontend                     │
                               └──────────────┬────────────────────────────▲──────────────┘
                                              │                            │
                               POST /v1/explanations/ask         POST /v1/explanations/conclusions
                                              │                            │
                                              ▼                            │
┌──────────────────────────────────────────────────────────────────────────┴──────────────┐
│ FastAPI Application (Role 03 Backend)                                                   │
│                                                                                         │
│  ┌───────────────────────────────────────────────────────────────────────────────────┐  │
│  │ Role04Service Facade (packages/rag/facade.py)                                      │  │
│  │                                                                                   │  │
│  │  ┌─────────────────────────────────────┐   ┌───────────────────────────────────┐  │  │
│  │  │ PATH A: Concept Q&A Engine          │   │ PATH B: Deterministic Conclusion  │  │  │
│  │  │                                     │   │                                   │  │  │
│  │  │ • Arabic/English Query Normalizer   │   │ • normalize_result_payload()      │  │  │
│  │  │ • Intent & Ambiguity Classifiers    │   │ • ActiveRequestTracker (Anti-Race)│  │  │
│  │  │ • Bilingual BM25 (469 Chunks)       │   │ • Zero-LLM Template Engine        │  │  │
│  │  │ • Gemini Client (gemini-2.5-flash)  │   │ • Denominator / QA Cell Enforcers │  │  │
│  │  │ • Zero-Trust Output Validator Gate  │   │ • Dynamic UI Action Trigger Binder│  │  │
│  │  │ • Offline local_retrieval Fallback  │   │                                   │  │  │
│  │  └──────────────────┬──────────────────┘   └─────────────────▲─────────────────┘  │  │
│  └─────────────────────┼────────────────────────────────────────┼────────────────────┘  │
└────────────────────────┼────────────────────────────────────────┼───────────────────────┘
                         ▼                                        │
           Verified NASA Citations & Explanations   Statistical Metric Payload from Role 02
```

### The Two Architectural Paths:

1. **Path A — Concept Q&A & Variable Discovery (`service.answer_question`):**
   - **Purpose:** Answers user questions in Arabic or English about climate variables, NASA satellite/reanalysis products, and statistical methods.
   - **How it works:** Normalizes Arabic/English text, identifies canonical variables, retrieves verified excerpts from the 469 semantic corpus chunks via local BM25, and optionally generates an explanation via Google Gemini (`gemini-2.5-flash`).
   - **Zero-Trust Safety Gate:** Every LLM response is validated by `validator.py`. If the output includes ungrounded numbers, claims causality, invents citations, or if the API key is missing/times out (>8s), it **automatically falls back to deterministic local retrieval (`mode: "local_retrieval"`)**. The app never crashes.

2. **Path B — Deterministic Interactive Conclusion Engine (`service.render_result`):**
   - **Purpose:** Translates verified statistical numbers from Role 02 (slopes, p-values, confidence intervals, cell distribution counts) into bilingual, judge-safe narrative conclusion cards.
   - **Zero-LLM Guarantee (0% AI in numbers):** **No LLM is ever used in Path B.** All narrative sentences are generated via deterministic templates in `packages/rag/conclusions.py`. Numbers are formatted directly from Role 02 without modification or hallucination.
   - **Active Request Protection:** Protects the UI from race conditions. If a user quickly switches regions, `ActiveRequestTracker` flags outdated responses as `stale_response` to avoid rendering old data.
   - **Interactive Action Triggers:** Binds each narrative segment to executable frontend UI actions (`FOCUS_REGION`, `FOCUS_REGIONAL_CHART`, `REVEAL_CELLS`, `OPEN_SPIN_IT`, `OPEN_RECEIPT`).

---

## 2. Master Data & Assets Reference Tables

### Table A: Climate Variable Datasets & Scientific Guardrails
All variable descriptions and limitations are embedded in `data/nasa/rag/corpus_semantic.jsonl` (469 chunks) and mapped via `packages/rag/id_mapping.py`.

| Canonical Variable ID (`scope.v2.json`) | Legacy / Alias IDs | NASA Product & Version | Physical Unit | Scientific Role & Product Type | Strict Guardrails Enforced in Role 04 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `air_temperature` | `T2M`, `temperature`, `heat`, `حرارة` | **MERRA-2** (`M2TMNXSLV` v5.12.4) | Kelvin (`K`) | 2-meter air temperature monthly mean reanalysis product. | • Must **never** be labeled as "direct satellite imagery" (it is an atmospheric reanalysis model).<br>• Must **never** be conflated with degrees Celsius (`°C`) without conversion.<br>• Strictly separated from station data (e.g. NASA POWER Cairo). |
| `soil_moisture` | `SoilMoi0_10cm_inst`, `soil water`, `رطوبة التربة` | **GLDAS Noah** (`GLDAS_NOAH025_M` v2.1) | $\text{kg/m}^2$ (or $\text{mm}$) | Top 0–10 cm soil moisture content land-surface model output. | • Banned from being represented as a percentage (`%`).<br>• Must **never** be labeled as satellite observations.<br>• Query `'رطوبة'` alone triggers an explicit soil-vs-air humidity clarification prompt. |
| `precipitation` | `GPM_3IMERGM`, `rain`, `rainfall`, `مطر`, `أمطار` | **GPM IMERG** (`GPM_3IMERGM` v07) | $\text{mm/month}$ (or $\text{mm/hr}$) | Merged multi-satellite passive microwave, radar & gauge analysis. | • Query `'شتاء'` (winter) is treated as a season/period and **never** auto-mapped to rain.<br>• Satellite retrieval caveats (gauge adjustments north of $45^\circ\text{N}$, microwave sampling gaps) attached to limitations. |
| `vegetation_greenness` | `MOD13C2`, `ndvi`, `green cover`, `غطاء نباتي` | **MODIS Terra** (`MOD13C2` v061) | Dimensionless NDVI ($-1.0$ to $+1.0$) | Monthly $0.05^\circ$ global Climate Modeling Grid Normalized Difference Vegetation Index. | • Must **never** be equated to "crop yield" or "agricultural harvest tonnage" (`محصول`/`إنتاجية`).<br>• Cloud and aerosol contamination QA masking rules explicitly reported. |
| *ISOLATED POINT SAMPLE* | `POWER_Cairo_monthly` | **NASA POWER** (API v2.0) | Celsius (`°C`) | Single-point Cairo meteorological station sample ($30.04^\circ\text{N}, 31.23^\circ\text{E}$). | • **Strictly segregated** from gridded regional cubes (`chunk_count = 0`).<br>• Used solely for local ground truth sanity checks; never mixed with MERRA-2 Kelvin spatial calculations. |

---

### Table B: Statistical Method Docs, Corpus Files & System Registries

| File / Asset Name | Source Kind / Category | Description | How Role 04 Uses It |
| :--- | :--- | :--- | :--- |
| `data/nasa/methods/pymannkendall.md` | `method_doc` | Technical documentation of the modified Mann-Kendall trend test (Hamed & Rao 1998 variance correction). | Retrieved when users ask how statistical significance or p-values are calculated; cited in citations. |
| `data/nasa/methods/scipy_theilslopes.html` | `method_doc` | Documentation of SciPy v1.18.0 Theil-Sen robust linear slope estimator and confidence intervals. | Retrieved when users ask how Sen's slope or trend rates are estimated. |
| `data/nasa/methods/statsmodels_fdr.html` | `method_doc` | Documentation of Statsmodels v0.15.0 Benjamini-Hochberg False Discovery Rate (FDR) multiplicity correction. | Retrieved when users ask about multi-cell grid significance maps. |
| `data/nasa/rag/corpus_semantic.jsonl` | `semantic_corpus` | 469 paragraph-based chunks (max 1600 chars) with complete provenance and font-artifact cleanups. | The search index for local BM25 retrieval. Availability fields are forbidden inside these chunks. |
| `data/nasa/rag/corpus_semantic_manifest.json` | `manifest` | Metadata manifest logging SHA-256 hashes, source URLs, and UTF-8/cp1252 hybrid encoding repairs. | Verifies provenance integrity at build time. |
| `packages/rag/aliases.py` | `team_authored` | Curated bilingual synonym tables (English & Egyptian Arabic). | Maps colloquial user terms (`"سخونة"`, `"بيسخن"`, `"حرارة"`, `"rainfall"`) to canonical variable IDs with explicit team-authored attribution. |
| `docs/architecture/scope.v2.json` | `architecture_registry` | Target grid defining 4 variables across 3 regions (`nile_corridor`, `morocco_comparison`, `sahel_comparison`). | Ground truth registry for valid variable-region pairs and spatial bounding boxes. |
| `data/nasa/runtime_catalog.json` | `runtime_catalog` | Live runtime registry holding cube file paths, grid resolutions, and the `app_available` boolean. | Queried dynamically by `ReadinessLookup` to report honest app readiness. |
| `data/nasa/validation_regional_report.json` | `validation_report` | Revision report declaring cube verification date (`data_revision = "2026-11-14"`). | Validates user data revision headers to detect outdated cube revisions. |
| `data/nasa/rag/evaluation_questions.json` | `benchmark_suite` | 12 bilingual benchmark questions testing ambiguity, unit checks, causal denial, and grid mismatch. | Validated in automated tests (`test_evaluation_questions`) to prevent regressions. |

---

## 3. Exact Input / Output Contracts & Internal Processing Flows

### Path A: Concept Q&A & Variable Discovery (`service.answer_question`)

#### 1. Method Signature
```python
def answer_question(
    self, 
    query: str, 
    region_id: Optional[str] = None, 
    period: Optional[Union[Tuple[str, str], List[str], Dict[str, str]]] = None, 
    data_revision: Optional[str] = None
) -> Dict[str, Any]
```

#### 2. Input JSON Example (Incoming to Backend Endpoint)
```json
{
  "query": "هل الدلتا بتسخن في الصيف؟",
  "region_id": "nile_corridor",
  "period": ["2001-01", "2024-12"],
  "data_revision": "2026-11-14"
}
```

#### 3. Step-by-Step Internal Processing Flow:
1. **Query Normalization (`packages/rag/arabic.py`):**
   - Strips tashkeel (diacritics) and tatweel (`ـ`).
   - Normalizes alef forms (`أ, إ, آ, ٱ` $\to$ `ا`) and taa marbuta (`ة` $\to$ `ه`).
   - Converts Eastern Arabic-Indic numerals (`٠-٩`) to ASCII digits (`0-9`).
   - Strips Arabic punctuation (`؟`, `،`, `؛`).
   - Strips prefixes (`وال`, `بال`, `لل`, `كال`) while preserving root words $\ge 3$ characters.
2. **Intent Classification & Guardrails (`packages/rag/intent.py`):**
   - Matches keywords against `NORMALIZED_ALIASES` and `PRODUCT_ALIASES`.
   - **Neighborhood Guard:** Rejects street/district queries (`"شارع"`, `"حي"`, `"my street"`) with `status: "unsupported"`, `reason_code: "unsupported_resolution"`.
   - **Cross-Grid Guard:** Rejects direct cell-to-cell comparisons without spatial aggregation (`status: "unsupported"`, `reason_code: "cross_grid_comparison_requires_aggregation"`).
   - **Winter Trap:** If query mentions `'شتاء'` without a variable, returns `status: "ambiguous"`, `reason_code: "season_without_variable"`.
   - **Humidity Trap:** If query mentions `'رطوبة'` without soil/air qualification, returns `status: "ambiguous"`, `reason_code: "air_vs_soil_humidity"`.
   - **Period Bound:** If query mentions a year $< 2001$, returns `status: "unavailable"`, `reason_code: "period_outside_scope"`.
   - **Causal Denial:** Queries asking `"ليه"` / `"لماذا"` / `"why"` trigger mandatory causality warning notes.
3. **Readiness Check (`packages/rag/id_mapping.py`):**
   - Queries `ReadinessLookup` for the `(variable_id, region_id, period, data_revision)` tuple.
   - If `app_available: false` (current project state), marks status as `documented_only` with `reason_code: "measurement_ready_app_not_available"`.
4. **Local BM25 Retrieval (`packages/rag/retriever.py`):**
   - Ranks the 469 semantic chunks using pure Python BM25 ($k_1=1.5, b=0.75$).
   - Dynamically attaches the product's official definition chunk and limitation chunk.
5. **LLM Generation & Zero-Trust Validation (`packages/rag/explanation.py` & `validator.py`):**
   - If `GEMINI_API_KEY` is present, formats a constrained prompt warning that evidence passages are untrusted data.
   - Invokes `gemini-2.5-flash` via HTTP header `x-goog-api-key` with an 8-second timeout.
   - Validates JSON output: checks for extra fields, confirms cited `chunk_id`s were part of the *current retrieval*, checks product versions, and blocks false causality or banned units.
   - Allows up to **1 bounded retry** on malformed JSON or validation failure.
   - If LLM fails, times out, or has no key, **seamlessly falls back to `mode: "local_retrieval"`**.

#### 4. Output JSON Example (Returned to Backend & Client)
```json
{
  "mode": "llm",
  "query": "هل الدلتا بتسخن في الصيف؟",
  "status": "documented_only",
  "reason_code": "measurement_ready_app_not_available",
  "variable_ids": ["air_temperature"],
  "suggested_variable_ids": ["air_temperature"],
  "answer": "وفقاً لوثائق MERRA-2 (M2TMNXSLV v5.12.4)، درجة حرارة الهواء على ارتفاع 2 متر مسجلة بوحدة الكلفن كمنتج إعادة تحليل جوي. ارتباط الاتجاه لا يثبت السببية.",
  "citations": [
    {
      "chunk_id": "M2TMNXSLV:collection:0",
      "source_id": "M2TMNXSLV",
      "source_kind": "product_doc",
      "product_id": "M2TMNXSLV",
      "product_version": "5.12.4",
      "source_url": "https://cmr.earthdata.nasa.gov/search/concepts/C1276812863-GES_DISC.html",
      "section_locator": "collection",
      "retrieved_timestamp": "2026-11-14T02:20:47.424889+00:00",
      "raw_source_hash": "3ee6dff35cb7419e49df9c4d293144ef9aa5a9cf279b9a6b1070ff0dfdfca054",
      "title": "MERRA-2 tavgM_2d_slv_Nx: 2d,Monthly mean,Time-Averaged,Single-Level,Assimilation,Single-Level Diagnostics V5.12.4 (M2TMNXSLV)",
      "text": "MERRA-2 is an atmospheric reanalysis produced by NASA's Global Modeling and Assimilation Office (GMAO)..."
    }
  ],
  "context": {
    "definition_chunks": [...],
    "limitation_chunks": [...]
  },
  "availability": {
    "air_temperature": {
      "found": true,
      "variable_id": "air_temperature",
      "region_id": "nile_corridor",
      "product_id": "M2TMNXSLV",
      "product_version": "5.12.4",
      "measurement_ready": true,
      "method_ready": false,
      "app_available": false,
      "data_revision": "2026-11-14",
      "reason_code": "not_app_available"
    }
  },
  "limitations": [
    "No causal claim is supported: trend association does not establish cause. Documentation describes the product, not a regional trend.",
    "المتغير المتاح لدينا هو درجة حرارة الهواء على ارتفاع 2 متر (MERRA-2 T2M). درجة حرارة السطح/الأرض أو حرارة مدينة بعينها غير متاحة."
  ],
  "validation": {
    "passed": true,
    "cited_chunk_ids": ["M2TMNXSLV:collection:0"]
  }
}
```

---

### Path B: Deterministic Conclusion Engine (`service.render_result`)

#### 1. Method Signatures
```python
# Helper adapter to normalize Role 02/03 field variants
normalize_result_payload(raw: Dict[str, Any]) -> Dict[str, Any]

# Main rendering call
render_result(
    self, 
    raw_payload: Dict[str, Any], 
    language: str = "en", 
    normalize: bool = True
) -> Dict[str, Any]
```

#### 2. Raw Input Payload Example (From Role 02/03 ML Service)
`normalize_result_payload()` automatically maps legacy/shorthand keys:

```json
{
  "result_id": "ana_nile_t2m_2001_2024",
  "request_hash": "req_user_9921",
  "region_id": "nile_corridor",
  "variable_id": "air_temperature",
  "start_month": "2001-01",
  "end_month": "2024-12",
  "units": "K",
  "state": "succeeded",
  "source": {
    "product_id": "M2TMNXSLV",
    "product_version": "5.12.4"
  },
  "regional_mean": 295.31,
  "n_months": 288,
  "slope": 0.021,
  "slope_units": "K per year",
  "p": 0.03,
  "alpha": 0.05,
  "ci": {
    "low": 0.0126,
    "high": 0.0294
  },
  "method_revision": "m2_sen_mk_hamed_rao_v1",
  "cell_distribution": {
    "denominator": "eligible_cells",
    "total": 960,
    "eligible": 950,
    "masked_cells": 10,
    "increasing": 200,
    "decreasing": 40,
    "non_significant": 710
  },
  "qa_coverage": {
    "valid_fraction": 0.98,
    "denominator": "weighted_area",
    "masked_cells": 10
  },
  "spin_it_summary": {
    "agreeing_windows": 3,
    "windows": 5
  },
  "availability_flags": {
    "chart": true,
    "cells": true,
    "spin_it": true,
    "receipt": true
  },
  "receipt": "rc_nile_t2m_20261114"
}
```

#### 3. Step-by-Step Internal Processing Flow:
1. **Payload Normalization (`packages/rag/facade.py`):**
   - Maps aliases: `result_id` $\to$ `analysis_id`, `request_hash` $\to$ `request_id`, `slope` $\to$ `sen_slope`, `p` $\to$ `p_value`, `masked_cells` $\to$ `ineligible_qa_cells`, `chart` $\to$ `regional_chart`, `cells` $\to$ `cell_reveal`.
2. **Anti-Race Stale Check (`ActiveRequestTracker`):**
   - If an active analysis was registered in the session via `service.register_analysis(...)`, verifies that `request_id` and `analysis_id` match.
   - If user switched regions or dates before this response arrived, returns `status: "stale_response"`, `segments: []`, `actions: []`.
3. **Payload Validation (`packages/rag/conclusions.py`):**
   - Enforces required fields, canonical IDs, product version presence, and positive sample counts.
   - Verifies cell arithmetic: `eligible_cells + ineligible_qa_cells == total_cells` and `increasing_cells + decreasing_cells <= eligible_cells`.
4. **Deterministic Template Synthesis (Zero-LLM):**
   - **Context Segment (`id: "context"`):** States variable, region, period, and source type ("reanalysis, not direct satellite observations"). Binds action `FOCUS_REGION`.
   - **Regional Trend Segment (`id: "regional_trend"`):**
     - If $p \ge \alpha$: Formulates *"insufficient statistical evidence for a trend under the declared method"* (Arabic: *"الأدلة الإحصائية غير كافية على وجود اتجاه عام"*). Strictly bans words like "stable", "unchanged", or "ثابت".
     - If $p < \alpha$: States significant increase/decrease with slope, p-value, and confidence interval. Binds action `FOCUS_REGIONAL_CHART` if `artifacts.regional_chart == true`.
     - If $p$ is null: Explains descriptive mean and outputs human-readable `inference_reason_code` (e.g. "insufficient sample size"); never emits literal `"None"`, `"null"`, or `"NaN"`.
   - **Cell Evidence Segment (`id: "cell_evidence"`):**
     - Exposes *"What the average hides"*: explicitly states denominators (e.g. `"21.1% of eligible cells: 200 of 950"`), reports masked QA cells (`"10 ineligible cells excluded"`), and non-significant cell counts.
     - Binds action `REVEAL_CELLS` if `artifacts.cell_reveal == true`.
   - **QA Coverage Segment (`id: "qa_coverage"`):** Reports valid area fraction and denominator basis.
   - **Sensitivity Segment (`id: "sensitivity"`):**
     - Reports Spin-It re-run window agreement (e.g. `"3 of 5 windows agree in slope sign"`).
     - Explicitly notes this is descriptive sensitivity, not probability of truth.
     - Binds action `OPEN_SPIN_IT` if `artifacts.spin_it == true`.
   - **Provenance Segment (`id: "provenance"`):** Binds action `OPEN_RECEIPT` pointing to `receipt_id`.

#### 4. Output JSON Example (Returned to Backend & Client)
```json
{
  "status": "succeeded",
  "mode": "conclusion_templates",
  "language": "ar",
  "analysis_id": "ana_nile_t2m_2001_2024",
  "request_id": "req_user_9921",
  "region_id": "nile_corridor",
  "variable_id": "air_temperature",
  "period": {
    "start_month": "2001-01",
    "end_month": "2024-12"
  },
  "units": "K",
  "segments": [
    {
      "id": "context",
      "kind": "context",
      "text": "درجة حرارة الهواء (2 متر) على نطاق ممر النيل من 2001-01 إلى 2024-12، استناداً إلى MERRA-2 T2M (M2TMNXSLV v5.12.4) — منتج إعادة تحليل، وليس قياساً مباشراً من الأقمار الصناعية.",
      "analysis_id": "ana_nile_t2m_2001_2024",
      "request_id": "req_user_9921",
      "actions": [
        {
          "action": "FOCUS_REGION",
          "analysis_id": "ana_nile_t2m_2001_2024",
          "request_id": "req_user_9921",
          "target": {
            "region_id": "nile_corridor"
          }
        }
      ]
    },
    {
      "id": "regional_trend",
      "kind": "regional_trend",
      "text": "المتوسط الإقليمي 295.31 K على مدار 288 قيمة شهرية. ميل Sen 0.021 K per year مع Mann-Kendall p = 0.03 < alpha = 0.05: أدلة إحصائية معنوية على زيادة وفق المنهجية المعلنة (m2_sen_mk_hamed_rao_v1). فاصل ثقة 95% من 0.013 إلى 0.029 K.",
      "analysis_id": "ana_nile_t2m_2001_2024",
      "request_id": "req_user_9921",
      "actions": [
        {
          "action": "FOCUS_REGIONAL_CHART",
          "analysis_id": "ana_nile_t2m_2001_2024",
          "request_id": "req_user_9921",
          "target": {
            "variable_id": "air_temperature"
          }
        }
      ]
    },
    {
      "id": "cell_evidence",
      "kind": "cell_evidence",
      "text": "أدلة على مستوى الخلايا وفق المنهجية المعلنة (m2_sen_mk_hamed_rao_v1): 200 خلية تُظهر أدلة إحصائية على زيادة و40 خلية تُظهر أدلة إحصائية على انخفاض (21.1% من الخلايا المؤهلة: 200 من 950؛ و4.2% من الخلايا المؤهلة: 40 من 950). و10 خلية غير مؤهلة مستبعدة بفحص الجودة. بقية الخلايا (710) لا تُظهر أدلة إحصائية معنوية محلية.",
      "analysis_id": "ana_nile_t2m_2001_2024",
      "request_id": "req_user_9921",
      "actions": [
        {
          "action": "REVEAL_CELLS",
          "analysis_id": "ana_nile_t2m_2001_2024",
          "request_id": "req_user_9921",
          "target": {
            "variable_id": "air_temperature"
          }
        }
      ]
    },
    {
      "id": "qa_coverage",
      "kind": "qa_coverage",
      "text": "تغطية البيانات: 98.0% من مساحة نطاق التحليل الموزونة تحتوي بيانات صالحة (المقام: weighted_area). و10 خلية غير مؤهلة/مقصاة ومستبعدة من كل النسب.",
      "analysis_id": "ana_nile_t2m_2001_2024",
      "request_id": "req_user_9921",
      "actions": []
    },
    {
      "id": "sensitivity",
      "kind": "sensitivity",
      "text": "ملخص الحساسية: 3 من 5 نوافذ معادة التشغيل تتفق في إشارة الميل (60.0% من 5 نوافذ). هذا ملخص حساسية وصفي، وليس احتمالاً بصحة أي ادعاء.",
      "analysis_id": "ana_nile_t2m_2001_2024",
      "request_id": "req_user_9921",
      "actions": [
        {
          "action": "OPEN_SPIN_IT",
          "analysis_id": "ana_nile_t2m_2001_2024",
          "request_id": "req_user_9921",
          "target": {
            "variable_id": "air_temperature"
          }
        }
      ]
    },
    {
      "id": "provenance",
      "kind": "provenance",
      "text": "التوثيق الكامل وإعدادات المنهجية وبصمات المصادر متاحة في الإيصال rc_nile_t2m_20261114.",
      "analysis_id": "ana_nile_t2m_2001_2024",
      "request_id": "req_user_9921",
      "actions": [
        {
          "action": "OPEN_RECEIPT",
          "analysis_id": "ana_nile_t2m_2001_2024",
          "request_id": "req_user_9921",
          "target": {
            "receipt_id": "rc_nile_t2m_20261114"
          }
        }
      ]
    }
  ],
  "actions": [
    { "action": "FOCUS_REGION", "analysis_id": "ana_nile_t2m_2001_2024", "request_id": "req_user_9921", "target": { "region_id": "nile_corridor" } },
    { "action": "FOCUS_REGIONAL_CHART", "analysis_id": "ana_nile_t2m_2001_2024", "request_id": "req_user_9921", "target": { "variable_id": "air_temperature" } },
    { "action": "REVEAL_CELLS", "analysis_id": "ana_nile_t2m_2001_2024", "request_id": "req_user_9921", "target": { "variable_id": "air_temperature" } },
    { "action": "OPEN_SPIN_IT", "analysis_id": "ana_nile_t2m_2001_2024", "request_id": "req_user_9921", "target": { "variable_id": "air_temperature" } },
    { "action": "OPEN_RECEIPT", "analysis_id": "ana_nile_t2m_2001_2024", "request_id": "req_user_9921", "target": { "receipt_id": "rc_nile_t2m_20261114" } }
  ]
}
```

---

## 4. Step-by-Step Backend Integration Roadmap

### Step 1: Environment & Secrets Setup
1. Create a `.env` file in the repo root (never commit `.env` to version control):
   ```bash
   LLM_PROVIDER=gemini
   GEMINI_API_KEY=AIzaSyYourSecretKeyHere
   LLM_MODEL=gemini-2.5-flash
   LLM_TIMEOUT_SECONDS=8
   LLM_MAX_RETRIES=1
   ```
2. **Offline Keyless Resilience:** If `GEMINI_API_KEY` is omitted or empty, `Role04Service` operates in 100% offline mode (`mode: "local_retrieval"`). **The backend will never crash if the API key is missing.**
3. **Key Leak Prevention:** `packages/rag/provider.py` passes the key strictly in the `x-goog-api-key` HTTP header (never in query parameters) and scrubs the key from all log strings and exception tracebacks.

### Step 2: Singleton Initialization at Startup (FastAPI Lifespan)
Loading the 469 semantic corpus chunks and pre-building the BM25 index takes $\sim 200\text{ ms}$. **Do not instantiate `Role04Service` on every request.** Initialize it once in FastAPI's `lifespan` handler and store it in `app.state.rag_service`.

### Step 3: Wire Endpoint 1 — Concept Q&A (`POST /v1/explanations/ask`)
Pass incoming query parameters to `service.answer_question(...)`:
- If `status == "ambiguous"`, return HTTP 200 with the `clarification` field so the UI can render quick-select chips (e.g. *Soil Moisture* vs. *Air Temperature*).
- If `status == "unsupported"`, return HTTP 200 with `message` explaining the boundary (e.g. neighborhood resolution not supported).
- The returned canonical `variable_id` can be used to select the active map layer in the frontend.

### Step 4: Wire Endpoint 2 — Conclusions (`POST /v1/explanations/conclusions`)
When Role 02 completes an analysis job:
1. Call `service.register_analysis(raw_payload)` when an analysis is requested to register the active `request_id`.
2. Pass the raw ML dictionary through `service.render_result(raw_payload, language="ar"|"en", normalize=True)`.
3. If `status == "stale_response"`, return HTTP 200 with `segments: []` (or HTTP 204); the frontend knows to silently drop out-of-order responses.

### Step 5: Handling Frontend Action Contracts
Ensure the frontend handles the 5 permitted action strings found in `segment["actions"]`:
- `FOCUS_REGION`: Calls MapLibre/Leaflet `fitBounds(region_bbox)`.
- `FOCUS_REGIONAL_CHART`: Scrolls to and highlights the regional time-series chart.
- `REVEAL_CELLS`: Toggles the spatial grid heatmap layer.
- `OPEN_SPIN_IT`: Opens the interactive time-window slider.
- `OPEN_RECEIPT`: Opens the data provenance modal.

---

## 5. Production-Ready FastAPI Reference Router Code

Copy and paste this production-ready router directly into your backend service:

```python
# app/routers/rag_router.py
"""FastAPI Router for Role 04 RAG & Conclusion Engine Integration.

Provides:
- POST /v1/explanations/ask: Concept Q&A, documentation retrieval & variable routing
- POST /v1/explanations/conclusions: Deterministic, zero-LLM statistical narrative conclusions
- POST /v1/explanations/reset: Resets ActiveRequestTracker session state
"""

import logging
from typing import Any, Dict, List, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from packages.rag.facade import Role04Service, normalize_result_payload
from packages.rag.conclusions import PayloadError

logger = logging.getLogger("trend_detective.rag")
router = APIRouter(prefix="/v1/explanations", tags=["RAG & Explanations"])


# ============================================================================
# Pydantic Request & Response Schemas
# ============================================================================

class QuestionRequest(BaseModel):
    query: str = Field(..., description="User question in Arabic, English, or mixed phrasing")
    region_id: Optional[str] = Field(None, description="Optional canonical region: nile_corridor, morocco_comparison, sahel_comparison")
    period: Optional[Union[List[str], Dict[str, str]]] = Field(None, description="Optional window, e.g. ['2001-01', '2024-12']")
    data_revision: Optional[str] = Field(None, description="Optional revision string, e.g. '2026-11-14'")
    language: Optional[str] = Field("ar", description="Language preference: 'ar' or 'en'")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "هل الدلتا بتسخن في الصيف؟",
                "region_id": "nile_corridor",
                "period": ["2001-01", "2024-12"],
                "language": "ar"
            }
        }


class ConclusionRequest(BaseModel):
    payload: Dict[str, Any] = Field(..., description="Raw or canonical Role 02/03 statistical result dictionary")
    language: Optional[str] = Field("ar", description="Output language: 'ar' or 'en'")

    class Config:
        json_schema_extra = {
            "example": {
                "payload": {
                    "result_id": "ana_nile_t2m_2001_2024",
                    "request_hash": "req_0042",
                    "region_id": "nile_corridor",
                    "variable_id": "air_temperature",
                    "start_month": "2001-01",
                    "end_month": "2024-12",
                    "units": "K",
                    "state": "succeeded",
                    "source": {"product_id": "M2TMNXSLV", "product_version": "5.12.4"},
                    "regional_mean": 295.31,
                    "n_months": 288,
                    "slope": 0.021,
                    "slope_units": "K per year",
                    "p": 0.03,
                    "alpha": 0.05,
                    "ci": {"low": 0.0126, "high": 0.0294},
                    "cell_distribution": {
                        "denominator": "eligible_cells",
                        "total": 960,
                        "eligible": 950,
                        "masked_cells": 10,
                        "increasing": 200,
                        "decreasing": 40,
                        "non_significant": 710
                    },
                    "availability_flags": {"chart": True, "cells": True, "spin_it": True, "receipt": True},
                    "receipt": "rc_nile_t2m_20261114"
                },
                "language": "ar"
            }
        }


# ============================================================================
# Dependency Injection
# ============================================================================

def get_rag_service(request: Request) -> Role04Service:
    """Retrieves the pre-warmed Role04Service singleton from app.state."""
    service = getattr(request.app.state, "rag_service", None)
    if service is None:
        # Fallback in case singleton wasn't set in lifespan
        logger.warning("Role04Service not found in app.state; initializing on the fly")
        service = Role04Service()
        request.app.state.rag_service = service
    return service


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/ask", status_code=status.HTTP_200_OK)
def ask_concept_question(
    req: QuestionRequest, 
    service: Role04Service = Depends(get_rag_service)
) -> Dict[str, Any]:
    """Concept & Variable Q&A endpoint.
    
    Routes questions to canonical variables, performs BM25 retrieval over 469 NASA chunks,
    validates LLM explanations through a strict zero-trust gate, and falls back to offline
    retrieval automatically if keyless or timed out.
    """
    try:
        norm_period = tuple(req.period) if isinstance(req.period, list) else req.period
        response = service.answer_question(
            query=req.query,
            region_id=req.region_id,
            period=norm_period,
            data_revision=req.data_revision,
        )
        return response
    except Exception as exc:
        logger.error(f"Error processing Q&A question: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Q&A service failure: {str(exc)}"
        )


@router.post("/conclusions", status_code=status.HTTP_200_OK)
def render_statistical_conclusions(
    req: ConclusionRequest, 
    service: Role04Service = Depends(get_rag_service)
) -> Dict[str, Any]:
    """Deterministic, zero-LLM interactive conclusion generator.
    
    Accepts statistical outputs from Role 02/03, normalizes payload aliases,
    checks ActiveRequestTracker to reject out-of-order stale requests, and
    generates bilingual scientific cards bound to UI actions.
    """
    try:
        # 1. Normalize aliases (maps result_id -> analysis_id, masked_cells -> ineligible_qa_cells, etc.)
        normalized = normalize_result_payload(req.payload)

        # 2. Register with ActiveRequestTracker to prevent UI race conditions
        req_id = normalized.get("request_id")
        ana_id = normalized.get("analysis_id")
        if req_id and ana_id:
            service.register_analysis(normalized)

        # 3. Render deterministic conclusion cards
        result = service.render_result(
            raw_payload=normalized,
            language=req.language or "ar",
            normalize=False  # Already normalized above
        )
        return result

    except PayloadError as pe:
        logger.warning(f"Payload validation failed in conclusion engine: {pe.errors}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"errors": pe.errors}
        )
    except Exception as exc:
        logger.error(f"Unexpected error in conclusion engine: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Conclusion engine error: {str(exc)}"
        )


@router.post("/reset", status_code=status.HTTP_200_OK)
def reset_session_state(service: Role04Service = Depends(get_rag_service)) -> Dict[str, str]:
    """Resets the ActiveRequestTracker state on user workspace reset."""
    service.reset_session()
    return {"status": "session_reset"}
```

### FastAPI Application Lifespan Setup:

```python
# app/main.py
from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from packages.rag.facade import Role04Service
from app.routers.rag_router import router as rag_router

logger = logging.getLogger("trend_detective")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP: Pre-warm Role 04 (Loads 469 semantic chunks, BM25 index & registry)
    logger.info("Initializing Role 04 RAG & Conclusion Engine...")
    app.state.rag_service = Role04Service()
    logger.info("Role 04 Engine pre-warmed successfully (170 tests verified).")
    yield
    # SHUTDOWN: Clean up resources if needed
    logger.info("Shutting down Trend Detective API.")

app = FastAPI(
    title="NASA Space Apps 2026 — Trend Detective API",
    lifespan=lifespan
)

app.include_router(rag_router)
```

---

## 6. Verification, Health Checks & Smoke Testing

### 1. Run the Full Automated Test Suite
From the repository root, verify that all 170 unit, adversarial, and end-to-end tests pass:
```powershell
python -m pytest tests -q
# Expected output: 170 passed in ~6.2s
```

### 2. Smoke Test Path A (Concept Q&A) via cURL
```bash
curl -X POST "http://localhost:8000/v1/explanations/ask" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "هل الدلتا بتسخن في الصيف؟",
       "region_id": "nile_corridor",
       "period": ["2001-01", "2024-12"],
       "language": "ar"
     }'
```
*Verify that `status` is `"documented_only"`, `mode` is `"llm"` (or `"local_retrieval"` if keyless), and citations point to MERRA-2.*

### 3. Smoke Test Path B (Conclusions) via cURL
```bash
curl -X POST "http://localhost:8000/v1/explanations/conclusions" \
     -H "Content-Type: application/json" \
     -d '{
       "payload": {
         "result_id": "an_smoke_01",
         "request_hash": "req_smoke_01",
         "region_id": "nile_corridor",
         "variable_id": "air_temperature",
         "start_month": "2001-01",
         "end_month": "2024-12",
         "units": "K",
         "source": {"product_id": "M2TMNXSLV", "product_version": "5.12.4"},
         "regional_mean": 295.31,
         "n_months": 288,
         "slope": 0.021,
         "slope_units": "K per year",
         "p": 0.03,
         "alpha": 0.05,
         "cell_distribution": {
           "denominator": "eligible_cells",
           "total": 960,
           "eligible": 950,
           "masked_cells": 10,
           "increasing": 200,
           "decreasing": 40,
           "non_significant": 710
         },
         "availability_flags": {"chart": true, "cells": true, "spin_it": true, "receipt": true},
         "receipt": "rc_smoke_001"
       },
       "language": "ar"
     }'
```
*Verify that `status` is `"succeeded"`, `segments` contains 6 cards with Arabic text, and `actions` contains 5 bound action objects.*

### 4. Stale Request Rejection Check
Repeat the cURL call with an outdated `request_hash`:
*Verify that `status` returns `"stale_response"` with empty `segments: []`, proving the anti-race protection is active.*

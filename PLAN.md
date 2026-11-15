# Trend Detective - Competition Architecture v2

Updated 14 November 2026. Supersedes the affected scope and ownership in earlier playbooks.

## Competition architecture v2

Decision record | 14 November 2026

### Committed scope

Trend Detective - What the Average Hides. Four connected variables, three bounded study windows, and monthly data from January 2001 through December 2024. The central experience asks: Does your conclusion survive changes in period, location and supporting evidence?

### Supersedes the earlier scope

This revision replaces the two-variable, one-domain scope and affected responsibilities in the previous team playbooks. Existing temperature and soil-moisture data remain useful inputs. This document specifies the expanded target; it does not claim the application or additional data already exist.

### Why four variables

Air temperature, precipitation, soil moisture and vegetation greenness provide distinct views of environmental change. A fifth variable has no defined additional user question at present. Strengthen quality screening, spatial comparison, reproducibility and presentation instead of expanding the catalog indefinitely.

### User and outcome

Students, science communicators and journalists select an area, inspect trends and uncertainty, test sensitivity and export evidence. Users can choose variables directly or ask a bilingual question. The tool supports investigation, not causal diagnosis or operational drought alerts.

### Boundaries

No invented combined drought score, neighborhood-level claims, global analysis promise or required LLM dependency. An opposite regional trend may not exist. Inconclusive results are valid outputs. The architecture is our competition recommendation, not evidence of guaranteed judging points.

### Delivery agreement

Six people own distinct modules and review their coding agents' output. Target submission is Sunday 15 November at 22:00 Egypt time, with the user-agreed work deadline at 23:59. Official portal constraints still need independent confirmation.

## Data scope and acquisition

Four variables | Twelve regional cubes

### Air temperature and soil moisture

MERRA-2 M2TMNXSLV v5.12.4: T2M, approximately 0.5-degree latitude by 0.625-degree longitude, K. GLDAS_NOAH025_M v2.1: SoilMoi0_10cm_inst, 0.25-degree grid, kg m-2 for the top 0-10 cm. These are reanalysis/model outputs, not direct independent station observations. Existing Egypt files passed ingestion checks.

### Precipitation - new acquisition

GPM_3IMERGM v07 Final Monthly, 0.1-degree grid. Confirm the actual precipitation variable, units, quality/error fields and fill rules from the files and version-specific guide. Convert a precipitation rate to a monthly amount only using the correct time integration; preserve original units and conversion provenance.

### Vegetation - new acquisition

MOD13C2 v061 monthly 0.05-degree CMG. Acquire NDVI with applicable QA/reliability fields, scale factors and fill values. Screen poor-quality observations before aggregation and report valid-area coverage. NDVI is a greenness indicator, not crop yield or a direct measure of plant health.

### Proposed windows: west, south, east, north

Nile corridor [29,24,33,32]; Morocco comparison [-10,30,-5,35]; Sahel comparison [-5,12,5,17]. These rectangles are not national boundaries or agricultural/irrigation masks. Freeze them after coverage/quality checks and before inspecting significance; later changes require a scope revision.

### Actual readiness gap

The verified Egypt rectangle [24,22,36,32] contains the proposed Nile window. Two target cubes can be derived from it. Ten cubes require new acquisition: GPM and MODIS in all three windows, plus MERRA-2 and GLDAS in the two additional windows. Target: 12 x 288 = 3,456 regional variable-month slices, not necessarily that many unique source files.

### No false availability

Each variable-region pair has its own readiness state. Keep new entries unavailable until actual files, QA and coverage pass validation. Reuse the existing data bundle without relabeling it as the expanded dataset.

## System components

One backend | Bounded jobs | Reproducible outputs

### Numerical data flow

NASA files and QA -> versioned ingestion -> native-grid regional cubes -> validated registry -> deterministic analysis worker -> cached result and receipt -> API -> map/charts. Documentation follows a separate route: cited corpus -> retrieval -> constrained LLM -> output validator -> explanation.

### Client

React, TypeScript and Vite; Leaflet for AOI and spatial layers; Plotly for time series and period matrices. The browser renders returned statistics rather than maintaining a second implementation. Core analysis remains usable when chat is disabled.

### Backend and storage

FastAPI, a bounded analysis worker, SQLite for job/receipt metadata, and files for cubes and derived arrays. Modules: catalog, ingestion, spatial aggregation, statistics, sensitivity, retrieval, explanations and export. No distributed microservice or vector-database requirement for this scope.

### Caching and idempotency

Normalize geometry/settings and hash the request with data and method revisions. Enforce one job per request hash using transactional job claiming. States: queued, running, succeeded, failed. Write output files atomically and publish a receipt only after validation. Ingestion retries transient errors with bounded backoff.

### Proposed operating limits

Start with one analysis worker, queue capacity 20 and a configurable 10,000-native-cell limit per request. Target cached showcase responses under two seconds; benchmark before claiming this performance. Longer work exposes progress. Restrict unsupported AOIs/periods with a useful explanation.

### Failure behavior

Missing source: disable that variable-region pair. Worker failure: explicit failed job and retry. LLM failure: deterministic evidence cards and excerpts. Basemap outage: locally cached boundaries and scientific layers on a plain background. Demo presets and citations must remain available offline.

## Scientific analysis contract

Inference is a gated feature, not a default label

### Time, units and QA

Use calendar-month IDs while preserving source timestamps. Decode scale/fill values and apply product-specific quality masks before aggregation. Never replace missing observations with zero. Record sample counts, valid-area fractions and minimum coverage rules. Freeze rules before inspecting trend significance.

### Spatial comparison

Keep native grids for each product's map. Aggregate each product over the same AOI using area-aware weights and explicit valid/land masks. Do not compare arbitrary pixels across grids. Regridding, if necessary, is an explicit versioned operation. Compute regional trends from regional time series, not an assumed average of cell slopes.

### Trend and uncertainty

Show monthly series and calendar-month anomalies. Use a documented Theil-Sen time basis and dependence-aware uncertainty procedure. Mann-Kendall/Hamed-Rao is a candidate, not an automatic guarantee. Member 2 freezes seasonal treatment, lag policy, autocorrelation correction and residual-block-bootstrap settings after controlled checks.

### Inference release gate

Do not display significance dots, p-values or confidence claims until the method passes review. Record resampling seed, replicate count, assumptions and method revision in receipts. Short or inadequate records return insufficient evidence. Non-significance is not proof of no change.

### Multiplicity and Spin It

Define the spatial test family for each variable and frozen study domain. Review the selected FDR procedure's dependence assumptions and expose raw p and adjusted q where appropriate. Spin It initially colors slopes only: overlapping period windows are not independently confirmed discoveries. Freeze minimum window length in advance.

### Interpretation limits

Show each variable's evidence separately. Shared model inputs can make products dependent, so agreement is not a count of independent votes. NDVI, rainfall and modeled soil moisture cannot establish irrigation or another causal explanation by themselves. The tool reports evidence and sensitivity, not a fabricated combined score.

## Investigation and grounded AI

Select -> inspect -> challenge -> compare -> reproduce

### Select and clarify

Draw an AOI inside an enabled study window or select a preset. Choose a variable or ask in Arabic/English. For Is this area drying?, explain which available variables test parts of the claim. Clarify air versus surface temperature and soil versus atmospheric humidity.

### Inspect the evidence

Use aligned cards for what, where, period, magnitude, units, uncertainty, coverage and source type. Show native-grid spatial trends beside the regional average. Missing source, failed analysis and inconclusive evidence are distinct states.

### Challenge the conclusion

Spin It shows start/end slope sensitivity. Educational headline templates are labeled. Reality Check restores the registered reference period. Any fraction of windows matching a sign includes its denominator and is labeled a sensitivity summary, not a probability that a claim is true.

### Compare locations

Compare the same variable and period across the three windows. Optional Find the Mirror searches a declared eligible family and discloses selection. It must return no qualifying contrast when appropriate. Do not imply that a selected extreme is representative or promise an opposite trend.

### RAG and output admission

Extend the existing corpus with version-specific GPM/MODIS and QA sources. Begin with BM25 and curated bilingual aliases; evaluate before adding embeddings. Require answer, cited_chunk_ids, suggested_variable_ids, result_references and limitations. Validate citations, availability and numeric references server-side.

### Trust boundary and receipt

Retrieved text is evidence, never executable instruction. The model cannot choose hidden method settings or compute scientific results. It receives verified result IDs and structured fields. Export CSV, normalized request, source hashes, revisions and a reproducible Python entry point. On model failure, use deterministic explanations.

## API and readiness contracts

Availability belongs to a variable-region pair

### Registry v2

Key entries by variable_id, region_id and data_revision. Include product/version, asset hash/path, bbox, native grid, coverage, units and QA policy. Separate measurement_ready, method_ready and app_available. The old pack's analysis_ready flag meant ingestion readiness, not a validated statistical pipeline.

### GET /v1/catalog

Expose actual availability plus clearly labeled planned entries. Default analysis controls list app_available entries only. Chat can explain planned datasets but cannot offer them as executable analyses. Availability in one region does not enable a variable everywhere.

### POST /v1/analyses

Accept region_id, AOI GeoJSON, variable_ids, start/end month, aggregation, method revision and data revisions. Validate coverage, geometry and compute limits, then return job_id, request_hash and state or a cached result. Development mocks must be visibly marked and never shipped as real measurements.

### GET /v1/analyses/{job_id}

Return progress and useful failed/insufficient-data reasons, then per-variable series, slope, units, sample counts, quality summaries and allowed uncertainty fields. Preserve full precision in stored results and consistent formatting in the UI.

### Explanations and receipts

POST /v1/explanations accepts a question and existing result_id. GET /v1/receipts/{id} provides data hashes, AOI, source granules, mask/aggregation policy, method settings, baseline, FDR family, seed and software revision. Repeated deterministic analyses must reproduce outputs within declared tolerance.

### Ownership and security

Member 1 signs measurement readiness; Member 2 signs method readiness; Member 6 checks integration before app_available becomes true. Member 3 owns contracts/state transitions. The AI cannot promote readiness. Keep Earthdata tokens and model keys outside frontend bundles, logs, exported receipts and archives.

## Owners 1 and 2

Data acquisition and scientific validity

### Member 1 - mission

Own product adapters, all twelve cubes, QA policies, study-window geometry and source lineage. Reuse verified Egypt data. Test one month of GPM and MODIS, including QA, before bulk acquisition. Verify variable identity, scale, units and missing masks from actual files.

### Member 1 - deliverables

Source manifest; study_windows.geojson; product preprocessing modules; qa_policy.json; data revisions and hashes; coverage reports; measurement-ready registry entries. Validate 288 unique months, coordinate order and decoded values. Deliver the first verified subset for every source/window by Saturday 13:00 and target the full bundle by 17:00.

### Member 1 - handoffs

Give representative cubes to Member 2 early and matching documentation to Member 4. Agents may build adapters/validators; the human reviews source identity and actual output. Do not silently interpolate missing periods or substitute a different product version.

### Member 2 - mission

Own aggregation, anomalies, slopes, uncertainty, autocorrelation handling, spatial multiplicity and period sensitivity. Maintain one implementation for maps and evidence cards. Freeze method_revision and minimum-series rules before releasing inference.

### Member 2 - deliverables

Analysis library, method_config.json and checks covering known slope, no trend, seasonality, serial dependence and missingness. Verify unit conversions and obtain at least one external reference comparison. Giovanni comparisons must reconcile product, period, mask, grid and weighting; they do not certify every statistical method.

### Member 2 - acceptance

No significance labels before the inference gate. Region slope comes from the aggregated series. Soil moisture is not percent; Celsius conversion is explicit; precipitation integration preserves units. Provide safe insufficient-data results and reviewed interpretation text to Members 3, 4 and 6.

## Owners 3 and 4

Backend contracts and grounded explanations

### Member 3 - mission

Own FastAPI, runtime registry, job queue, caching, SQLite metadata, receipts and deployment. Publish API models and sample contracts by Saturday 11:00. Keep ingestion separate from user requests. Build an actual temperature analysis path by 17:00.

### Member 3 - deliverables

Catalog, analysis submission/polling, explanation and receipt endpoints; health checks; explicit error codes; environment configuration; local start command. Cache keys include data and method revisions. A failed job must not create a successful-looking receipt.

### Member 3 - acceptance

Check duplicate requests, unavailable source rejection, interrupted-worker recovery, stale-cache invalidation and secret exclusion. Benchmark actual showcase performance before setting UI promises. Publish contract changes to Members 4-6 rather than changing schemas independently.

### Member 4 - mission

Own bilingual interpretation, product/version-aware retrieval, citations, result-grounded explanations and fallback. Extend the 315 nonempty source chunks with the new products and QA guides. Distinguish official evidence from team-authored aliases, prompts and evaluation cases.

### Member 4 - deliverables

Versioned corpus/index; retrieval adapter; strict explanation schema; answer validator; evaluation report. Cases must include unavailable regions, air/surface ambiguity, NDVI limits, units, false causality, missing data and malicious instructions embedded in retrieved text. Numeric claims reference verified result fields.

### Member 4 - acceptance

All citations resolve to retrieved chunks; all executable suggestions match AOI/period availability. The model cannot silently change statistical settings. Agents may build retrieval/evaluation harnesses; the human reviews failures. If integration is unstable, ship deterministic explanations and useful source excerpts.

## Owners 5 and 6

Spatial UX, integration and presentation

### Member 5 - mission

Own window selection, AOI drawing, variable browser, native-grid layers, legends, evidence cards and bilingual layout. Show loaded boundaries and coverage. Restrict selections to supported data and sensible resolution; do not imply neighborhood precision by visual interpolation.

### Member 5 - deliverables

Responsive map flow; keyboard-accessible controls; loading, error and insufficient-data states; product-specific units and legends. Ensure QA masking is consistent between maps and regional series. On basemap failure, show cached boundaries and data on a plain background with attribution.

### Member 5 - acceptance

A new user can choose an area/variable, inspect a real result and identify its main limitation. NDVI and rain do not inherit temperature labels or color conventions accidentally. Share stable selection state and event contracts with Member 6.

### Member 6 - mission

Own time series, Spin It, Reality Check, region comparison, receipt export and end-to-end integration. Coordinate early integration instead of collecting last-minute bugs. Reserve presentation time and build the real-data path before decorative animation.

### Member 6 - deliverables

Reproducible demo preset, acceptance checklist, offline build, recorded fallback and a 60-90 second presentation. Flow: select -> evidence -> sensitivity -> spatial contrast -> receipt. Choose examples from actual results, disclose discovery selection and never fabricate a reversal.

### Member 6 - release checks

Verify readiness, citations, units, numeric consistency, export reopening and behavior with network/LLM disabled. Each module owner reviews agent-generated changes. API and method changes require their designated owner review. Keep source credits and project submission materials complete.

## Delivery gates and scope control

Egypt time | 14-15 November 2026

### Saturday 09:00-13:00

Freeze v2 owners and proposed windows. Publish contracts by 11:00. By 13:00 verify a real monthly subset from each new product and confirm QA/coverage in all windows. Freeze window definitions before comparing significance. Declare access or quality blockers immediately.

### Saturday 13:00-21:00

Target all twelve cubes and one integrated real-data analysis by 17:00. By 21:00 target selectable four-variable evidence cards in the Nile window, spatial reveal, a reviewed method configuration and cited explanations or deterministic fallback. Other windows must use the same processing path.

### Sunday 09:00-14:00

By 11:00 target four variables across three windows, Spin It, comparisons and receipts. By 14:00 complete the external cross-check, missing-data audit, uncertainty/multiplicity review and end-to-end checks. Never release unsupported statistical claims to satisfy the clock.

### Sunday 14:00-23:59

Usability fixes and rehearsals until 17:00; then feature freeze. Finish source credits, README, project description, video and offline fallback by 20:00. Team submission target 22:00; user-agreed work deadline 23:59. Verify official portal requirements separately.

### If a gate fails

First remove optional narration, animations and automatic Mirror search. If a product cannot pass data/QA checks by Sunday 11:00, disable it and explicitly report the delivered scope. Preserve the target in planning but never label missing functionality complete or substitute synthetic evidence.

### Definition of done

Twelve verified cubes; enabled-variable selection and AOI; reviewed trend/coverage reporting; spatial reveal; slope-only period sensitivity unless extra inference is justified; region comparison; grounded explanation/fallback; reproducible receipt; offline showcase and presentation. Additional variables or regions require a scope revision.

## Sources and verified starting point

Evidence, implementation status and provenance

### Existing measurements

The current Egypt pack has 576 monthly subsets and two combined cubes. Temperature: 114,912 finite values and no missing cells. Soil moisture: 484,704 finite values; 237 cells missing throughout all 288 months; no partially missing cells. Monthly arrays exactly match combined cubes. These are ingestion checks, not climate conclusions.

### What remains planned

GPM, MODIS and Morocco/Sahel extensions are not downloaded in this revision. Their v2 registry entries remain unavailable. Statistical methods, UI, inference validation and new RAG evaluations are implementation work. The existing data ZIP is still a two-variable Egypt pack.

### Official challenge

https://www.spaceappschallenge.org/2026/challenges/earth-system-trend-detective/
Use the official challenge as the requirements source. Do not present historical judging guidance as a verified 2026 rubric.

### NASA products

MERRA-2: https://doi.org/10.5067/AP1B0BA5PD2K
GLDAS: https://doi.org/10.5067/SXAVCZFAQLNO
GPM: https://doi.org/10.5067/GPM/IMERG/3B-MONTH/07
MODIS: https://doi.org/10.5067/MODIS/MOD13C2.061

### Methods and access

https://earthaccess.readthedocs.io/en/stable/user/explanation/authenticate/
https://github.com/mmhs013/pyMannKendall
https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.theilslopes.html
https://www.statsmodels.org/stable/generated/statsmodels.stats.multitest.multipletests.html

### Design lineage

The enterprise-system-design skill informed explicit ownership, state transitions, retries and separation of model generation from output admission. Its ai-systems/05-generation-termination-and-output-admission.md reference shaped schema, evidence and availability checks. These are engineering choices, not NASA requirements.
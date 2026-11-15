# Open Questions and Recorded Decisions

This file records conflicts found between the repository documentation and the backend
brief, the decision taken, and what still needs another owner's confirmation.

Status legend: **DECIDED** (implemented, reversible) · **OPEN** (needs another team).

---

## 1. Region bbox: two files disagree — DECIDED

`data/nasa/runtime_catalog.json` describes the Egypt rectangle as
`[24, 22, 36, 32]`. `docs/architecture/scope.v2.json` defines `nile_corridor` as
`[29, 24, 33, 32]`.

**Decision:** the newer target scope (`scope.v2.json`) wins, because the delivered cubes
are described there and the region id `nile_corridor` is what the frontend will use.
The older bbox is not exposed.

**Needs:** Role 01 to confirm which rectangle is authoritative for the Nile window.

---

## 2. Variable and region ids differ from the brief's examples — DECIDED

The brief used `air_temperature`, `soil_moisture`, `precipitation`, `ndvi` and the region
`egypt`. The repository uses `vegetation_greenness` (not `ndvi`) and `nile_corridor`
(not `egypt`).

**Decision:** canonical ids come from `scope.v2.json`. Aliases (`ndvi`, `egypt`, `T2M`,
`morocco`, `sahel`, `rain`, …) are resolved on input, so both spellings work. Responses
always return the canonical id, which keeps cache keys and receipts unambiguous.

**Needs:** nothing, unless Role 01 introduces different canonical ids.

---

## 3. Readiness flags make every analysis technically unavailable — DECIDED

`scope.v2.json` reports `measurement_ready: true` but `method_ready: false` and
`app_available: false` for all twelve entries. Taken literally, `POST /v1/analyses` should
reject every request.

**Decision:** keep the verified flags truthful and add a separate mock gate,
`demo_available`. `/catalog/availability` returns both, plus
`availability_source: "registry_snapshot + mock_demo_gate"` and `simulated: true`.
Analyses run only through the demo gate and every result is labelled `data_mode: "mock"`.

**Needs:** Role 02 to supply a reviewed method so `method_ready` can become true.

---

## 4. Spin It example years exceed the base result period — DECIDED

The brief pairs a base analysis of `2005-01 .. 2020-12` with a Spin It request of
`start_year_min: 2001, end_year_max: 2024`. Those years are outside the base result.

**Decision:** the brief also requires validating that selected years fall inside the base
result period, so that rule wins. Out-of-range years return **422 `INVALID_SPIN_WINDOW`**
with `details.coverage`. The documented example therefore uses a base analysis of
`2001-01 .. 2024-12`, which matches the delivered data period.

**Needs:** confirmation that rejecting (rather than clamping) is the desired UX.

---

## 5. UI action identifiers are proposals — OPEN

`FOCUS_REGION`, `FOCUS_REGIONAL_CHART`, `REVEAL_CELLS`, `OPEN_SPIN_IT`, `OPEN_RECEIPT`
are emitted by `/v1/explanations`. They come from the brief and from the Role 04 brief,
but no frontend contract confirms them.

**Needs:** Role 05/06 to confirm the action enum and payload shape. Until then the
identifiers are additive: adding or renaming one does not change the rest of the schema.

---

## 6. Units for precipitation and NDVI are not in the repository — OPEN

`runtime_catalog.json` asserts units only for T2M (`K`) and `SoilMoi0_10cm_inst`
(`kg m-2`). GPM IMERG and MOD13C2 units appear in the catalog snapshot but are marked
`units_verified: false` with an explicit `unit_source` note and a `UNIT_UNVERIFIED`
warning.

**Needs:** Role 01 to add product documentation or registry entries so the units can be
verified, or to correct them.

---

## 7. Regional comparison is not implemented — OPEN

`POST /v1/comparisons` accepts only `comparison_type: "cells"`. Regional comparison
needs two completed results and a compatibility check across variable, unit, period,
method version and dataset revision.

**Decision:** the schema already carries a `compatibility` block and an open
`comparison_type` enum so regional support can be added without breaking clients.

**Needs:** agreement on whether cross-region comparison is in scope for the demo.

---

## 8. Recommendation endpoint was optional in the Role 04 brief — DECIDED

`AGENT_BRIEF.md` says a standalone recommendation endpoint "is optional and must be
agreed with Role 03; it is not an already implemented `/api/recommend` contract".

**Decision:** implemented as `POST /v1/recommendations` because the backend brief
requires it, and the path follows the `/v1` versioning rule. No `/api/recommend` alias is
exposed. The recommendation logic sits behind `RAGAdapter`, so Role 04 can replace it.

**Needs:** Role 03/04 sign-off on the path and response shape.

---

## 9. `analysis_ready` in the legacy registry means ingestion readiness — DECIDED

`runtime_catalog.json` sets `analysis_ready: true` for T2M and soil moisture, but the
architecture states that flag means ingestion readiness only.

**Decision:** the legacy flag is not surfaced. The API exposes `measurement_ready`,
`method_ready` and `app_available` separately, plus a derived `availability_state`
(`catalogued` < `measurement_ready` < `analysis_ready`).

**Needs:** nothing.

---

## 10. Spatial analysis uses the first requested variable — OPEN

Multi-variable analyses are accepted (up to four), but the spatial grid and Spin It
operate on `variable_ids[0]`. The response does not currently state which variable the
grid represents beyond `variable_id` inside each cell.

**Needs:** product decision — either restrict spatial to single-variable results, or add
a `?variable_id=` selector to `/spatial`.

---

## 11. No persistence — OPEN

All state is in-process and lost on restart; uvicorn multi-worker deployments would not
share state.

**Needs:** deployment target and workload shape before choosing SQLite/PostgreSQL plus a
durable job runner. Repository protocols are already in place.

---

## 12. FastAPI drops `AfterValidator` on query parameters — DECIDED (workaround)

`MonthStr` (`Annotated[str, AfterValidator(...)]`) is enforced for request bodies but not
for query parameters in FastAPI 0.163, which produced a 500 on `start_month=2005-13`.

**Decision:** `/catalog/availability` adds an explicit `pattern` to both month query
parameters, and `evaluate_demo_availability()` also guards the format defensively.
Result: 422 instead of 500. Body validation still uses `MonthStr`.

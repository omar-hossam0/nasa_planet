"""Variable recommendations from a natural-language question."""

from __future__ import annotations

from app.adapters.interfaces import NASADataAdapter, RAGAdapter
from app.core.config import Settings
from app.core.exceptions import (
    InvalidPeriodError,
    RegionNotFoundError,
    RequestValidationAppError,
)
from app.core.timeutil import month_to_index
from app.mocks.ai import RATIONALE
from app.schemas.recommendation import (
    CandidateVariable,
    RecommendationContext,
    RecommendationRequest,
    RecommendationResponse,
    RecommendationStatus,
)


class RecommendationService:
    def __init__(self, data: NASADataAdapter, rag: RAGAdapter, settings: Settings) -> None:
        self._data = data
        self._rag = rag
        self._settings = settings

    def recommend(self, request: RecommendationRequest) -> RecommendationResponse:
        if len(request.question) > self._settings.max_question_length:
            raise RequestValidationAppError(
                f"question must not exceed {self._settings.max_question_length} characters.",
                details={"length": len(request.question)},
            )

        region_known: bool | None = None
        if request.region_id:
            resolved = self._data.resolve_region_id(request.region_id)
            if resolved is None:
                raise RegionNotFoundError(
                    request.region_id,
                    known=[region.region_id for region in self._data.list_regions()],
                )
            region_known = True
        elif request.region_id is not None:
            region_known = False

        if request.start_month and request.end_month:
            if month_to_index(request.start_month) > month_to_index(request.end_month):
                raise InvalidPeriodError(
                    "start_month must not be later than end_month.",
                    start_month=request.start_month,
                    end_month=request.end_month,
                )

        outcome = self._rag.recommend(request.question, request.language)

        candidates: list[CandidateVariable] = []
        for variable_id in outcome.variable_ids:
            record = self._data.get_variable(variable_id)
            if record is None:
                continue  # never recommend an id the catalog does not contain
            candidates.append(
                CandidateVariable(
                    variable_id=record.variable_id,
                    display_name=record.display_name,
                    unit=record.unit,
                    confidence=outcome.confidence.get(variable_id, 0.5),
                    rationale=RATIONALE.get(variable_id, "Matched a demo keyword rule."),
                    demo_available=record.demo_available,
                    measurement_ready=record.measurement_ready,
                )
            )

        if outcome.status is RecommendationStatus.recommended and not candidates:
            # Defensive: rules matched but nothing survived catalog validation.
            status = RecommendationStatus.unsupported
            message = "No catalog variable matched the question."
        else:
            status = outcome.status
            message = {
                RecommendationStatus.recommended: (
                    "Deterministic keyword match against the demo catalog. "
                    "No retrieval or model was used."
                ),
                RecommendationStatus.clarification_required: (
                    "The question is ambiguous for this catalog; a clarification is required."
                ),
                RecommendationStatus.unsupported: (
                    "The question does not match any variable in scope. "
                    "Supported variables: air_temperature, soil_moisture, precipitation, "
                    "vegetation_greenness."
                ),
            }[status]

        return RecommendationResponse(
            status=status,
            question=request.question,
            language=request.language,
            candidates=candidates,
            clarification_question=outcome.clarification_question,
            message=message,
            context=RecommendationContext(
                region_id=request.region_id,
                region_known=region_known,
                start_month=request.start_month,
                end_month=request.end_month,
            ),
            warnings=[
                "Mock recommendation engine: keyword rules, not an LLM or a retrieval system.",
                "No citation is returned because nothing was retrieved.",
            ],
        )

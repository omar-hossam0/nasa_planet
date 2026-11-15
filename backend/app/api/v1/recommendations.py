"""Mock recommendation endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.dependencies import Container, get_container
from app.schemas.common import ErrorEnvelope
from app.schemas.recommendation import RecommendationRequest, RecommendationResponse

router = APIRouter(tags=["recommendations"])


@router.post(
    "/recommendations",
    response_model=RecommendationResponse,
    summary="Suggest variables for a natural-language question",
    description=(
        "Deterministic keyword rules over the demo catalog. No LLM is called and nothing is "
        "retrieved, therefore `references` is always empty. The adapter behind this endpoint "
        "is replaceable by the AI team's RAG implementation without changing the contract."
    ),
    responses={
        404: {"model": ErrorEnvelope, "description": "Unknown region id."},
        422: {"model": ErrorEnvelope, "description": "Invalid question, language or period."},
    },
)
def create_recommendation(
    payload: RecommendationRequest,
    container: Container = Depends(get_container),
) -> RecommendationResponse:
    return container.recommendation.recommend(payload)

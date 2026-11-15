"""Explanation endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.dependencies import Container, get_container
from app.schemas.common import ErrorEnvelope
from app.schemas.explanation import ExplanationRequest, ExplanationResponse

router = APIRouter(tags=["explanations"])


@router.post(
    "/explanations",
    response_model=ExplanationResponse,
    summary="Explain a completed result",
    description=(
        'Deterministic bilingual result report rendered from stored statistics and scientific templates. No LLM is called.'
    ),
    responses={
        404: {"model": ErrorEnvelope, "description": "Unknown result id."},
        409: {"model": ErrorEnvelope, "description": "Result exists but its job is not complete."},
        422: {"model": ErrorEnvelope, "description": "Unsupported language or invalid body."},
    },
)
def create_explanation(
    payload: ExplanationRequest,
    container: Container = Depends(get_container),
) -> ExplanationResponse:
    return container.explanation.explain(payload)

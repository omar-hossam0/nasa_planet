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
        "Template-rendered explanation built only from fields already stored in the result. "
        "No model is called, no number is invented and `references` is empty because nothing "
        "was retrieved. English and Arabic are supported at the contract level."
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

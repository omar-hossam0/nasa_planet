"""Analysis creation and job polling."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from app.core.dependencies import Container, get_container
from app.schemas.analysis import AnalysisAcceptedResponse, AnalysisRequest, JobStatusResponse
from app.schemas.common import ErrorEnvelope

router = APIRouter(tags=["analyses"])


@router.post(
    "/analyses",
    response_model=AnalysisAcceptedResponse,
    status_code=202,
    summary="Create a trend analysis",
    description=(
        "Validates the request, then creates a mock job. Returns **202** for new work and **200** "
        "when an equivalent analysis already exists (identical variables, AOI, period, policy, "
        "dataset revision and method version). Execution is deterministic and completes inline, "
        "so the job is immediately pollable."
    ),
    responses={
        200: {"model": AnalysisAcceptedResponse, "description": "Equivalent analysis reused."},
        404: {"model": ErrorEnvelope, "description": "Unknown variable or region id."},
        409: {"model": ErrorEnvelope, "description": "Requested data is not available."},
        422: {"model": ErrorEnvelope, "description": "Invalid AOI, period or aggregation policy."},
    },
)
def create_analysis(
    payload: AnalysisRequest,
    response: Response,
    container: Container = Depends(get_container),
) -> AnalysisAcceptedResponse:
    accepted, created = container.analysis.create_analysis(payload)
    if not created:
        response.status_code = 200
    return accepted


@router.get(
    "/analyses/{job_id}",
    response_model=JobStatusResponse,
    summary="Poll an analysis job",
    description="Returns `queued | running | completed | failed` plus the result id when available.",
    responses={404: {"model": ErrorEnvelope, "description": "Unknown job id."}},
)
def get_job(job_id: str, container: Container = Depends(get_container)) -> JobStatusResponse:
    return container.analysis.get_job(job_id)

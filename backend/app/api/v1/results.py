"""Completed result retrieval."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.dependencies import Container, get_container
from app.schemas.common import ErrorEnvelope
from app.schemas.results import ResultResponse

router = APIRouter(tags=["results"])


@router.get(
    "/results/{result_id}",
    response_model=ResultResponse,
    summary="Get a completed analysis result",
    description=(
        "Returns the stored synthetic result: requested variables, region/AOI, period, monthly "
        "series, descriptive trend, units, evidence state and warnings. Results only exist for "
        "completed jobs."
    ),
    responses={404: {"model": ErrorEnvelope, "description": "Unknown result id."}},
)
def get_result(result_id: str, container: Container = Depends(get_container)) -> ResultResponse:
    return container.result.get_result(result_id)

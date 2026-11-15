"""Cell comparison endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.dependencies import Container, get_container
from app.schemas.common import ErrorEnvelope
from app.schemas.comparison import ComparisonRequest, ComparisonResponse

router = APIRouter(tags=["comparisons"])


@router.post(
    "/comparisons",
    response_model=ComparisonResponse,
    summary="Compare two or more grid cells",
    description=(
        "Chart-ready comparison of cells belonging to the same result. A compatibility report "
        "documents variable/unit/period/method/revision agreement. Cells without data are "
        "rejected with 409 rather than compared as zero. The schema is additive-safe for future "
        "regional comparisons."
    ),
    responses={
        404: {"model": ErrorEnvelope, "description": "Unknown result or cell id."},
        409: {"model": ErrorEnvelope, "description": "Incomparable cells or unsupported comparison type."},
        422: {"model": ErrorEnvelope, "description": "Invalid request body."},
    },
)
def create_comparison(
    payload: ComparisonRequest,
    container: Container = Depends(get_container),
) -> ComparisonResponse:
    return container.comparison.compare(payload)

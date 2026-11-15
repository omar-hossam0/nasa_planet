"""Spatial grid and cell detail."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.dependencies import Container, get_container
from app.schemas.common import ErrorEnvelope
from app.schemas.spatial import CellDetailResponse, SpatialResponse

router = APIRouter(tags=["spatial"])


@router.get(
    "/results/{result_id}/spatial",
    response_model=SpatialResponse,
    summary="Map-ready spatial grid for a result",
    description=(
        "Returns a small deterministic 3x3 lon/lat grid. Each cell carries a GeoJSON polygon, "
        "bbox, centroid, synthetic trend, unit, evidence state and a missing-data flag."
    ),
    responses={404: {"model": ErrorEnvelope, "description": "Unknown result id."}},
)
def get_spatial(result_id: str, container: Container = Depends(get_container)) -> SpatialResponse:
    return container.spatial.get_spatial(result_id)


@router.get(
    "/results/{result_id}/cells/{cell_id}",
    response_model=CellDetailResponse,
    summary="Detail for one grid cell",
    description="Returns the cell's geometry, monthly series, trend and warnings.",
    responses={404: {"model": ErrorEnvelope, "description": "Unknown result or cell id."}},
)
def get_cell(
    result_id: str,
    cell_id: str,
    container: Container = Depends(get_container),
) -> CellDetailResponse:
    return container.spatial.get_cell(result_id, cell_id)

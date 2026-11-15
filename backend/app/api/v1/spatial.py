"""Spatial grid and cell detail."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.dependencies import Container, get_container
from app.schemas.common import ErrorEnvelope
from app.schemas.spatial import CellDetailResponse, SpatialResponse, CompactSpatialResponse

router = APIRouter(tags=["spatial"])


@router.get(
    "/results/{result_id}/spatial",
    response_model=SpatialResponse | CompactSpatialResponse,
    summary="Map-ready spatial grid for a result",
    description=(
        'Returns the configured native science grid or explicit demo cells. Use compact=true for grid arrays without repeated cell geometries.'
    ),
    responses={404: {"model": ErrorEnvelope, "description": "Unknown result id."}},
)
def get_spatial(result_id: str, compact: bool = False, container: Container = Depends(get_container)):
    return container.spatial.get_spatial(result_id,compact=compact)


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

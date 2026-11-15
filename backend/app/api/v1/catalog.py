"""Catalog endpoints: variables, regions, availability."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import Container, get_container
from app.schemas.catalog import (
    AvailabilityResponse,
    CatalogResponse,
    RegionsResponse,
    VariableDetail,
)
from app.schemas.common import ErrorEnvelope, MonthStr

router = APIRouter(tags=["catalog"])

_NOT_FOUND = {"model": ErrorEnvelope, "description": "Unknown variable or region id."}


@router.get(
    "/catalog",
    response_model=CatalogResponse,
    summary="List catalogued environmental variables",
    description=(
        "Returns every known variable with provenance and three separate readiness flags. "
        "A catalogued variable is not automatically ready for scientific analysis."
    ),
)
def list_variables(container: Container = Depends(get_container)) -> CatalogResponse:
    return container.catalog.list_variables()


@router.get(
    "/catalog/variables/{variable_id}",
    response_model=VariableDetail,
    summary="Variable metadata",
    responses={404: _NOT_FOUND},
)
def get_variable(
    variable_id: str,
    container: Container = Depends(get_container),
) -> VariableDetail:
    return container.catalog.get_variable(variable_id)


@router.get(
    "/catalog/regions",
    response_model=RegionsResponse,
    summary="List study regions",
    description="Study windows, not administrative boundaries. All records are demo-only.",
)
def list_regions(container: Container = Depends(get_container)) -> RegionsResponse:
    return container.catalog.list_regions()


@router.get(
    "/catalog/availability",
    response_model=AvailabilityResponse,
    summary="Check whether a variable/region/period is usable",
    description=(
        "Combines registry-verified readiness with the mock demo gate. `simulated=true` means the "
        "answer is mock-simulated; the `measurement_ready` / `method_ready` / `app_available` "
        "fields are copied from the verified registry snapshot."
    ),
    responses={404: _NOT_FOUND, 422: {"model": ErrorEnvelope, "description": "Invalid bbox or period."}},
)
def check_availability(
    variable_id: str = Query(..., examples=["air_temperature"]),
    region_id: str = Query(..., examples=["nile_corridor"]),
    start_month: MonthStr = Query(
        ...,
        pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
        description="First month of the period, format YYYY-MM.",
        examples=["2005-01"],
    ),
    end_month: MonthStr = Query(
        ...,
        pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
        description="Last month of the period, format YYYY-MM.",
        examples=["2020-12"],
    ),
    bbox: str | None = Query(
        default=None,
        description="Optional 'west,south,east,north' comma-separated bbox in WGS84 degrees.",
        examples=["29.0,24.0,33.0,32.0"],
    ),
    container: Container = Depends(get_container),
) -> AvailabilityResponse:
    return container.catalog.check_availability(
        variable_id=variable_id,
        region_id=region_id,
        start_month=start_month,
        end_month=end_month,
        bbox=bbox,
    )

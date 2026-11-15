"""Spin It endpoints: start and retrieve a time-window sensitivity run."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.dependencies import Container, get_container
from app.schemas.common import ErrorEnvelope
from app.schemas.spin import SpinCreateResponse, SpinRequest, SpinResponse

router = APIRouter(tags=["spin"])


@router.post(
    "/results/{result_id}/spin",
    response_model=SpinCreateResponse,
    status_code=202,
    summary="Start a Spin It time-window sweep",
    description=(
        "Slides a fixed-length window across the parent result's period, one year per step. "
        "The parent result is never modified. Output is deterministic synthetic data."
    ),
    responses={
        404: {"model": ErrorEnvelope, "description": "Unknown result id."},
        422: {"model": ErrorEnvelope, "description": "Invalid window bounds."},
    },
)
def create_spin(
    result_id: str,
    payload: SpinRequest,
    container: Container = Depends(get_container),
) -> SpinCreateResponse:
    return container.spin.create_spin(result_id, payload)


@router.get(
    "/spin/{spin_id}",
    response_model=SpinResponse,
    summary="Retrieve a Spin It operation",
    responses={404: {"model": ErrorEnvelope, "description": "Unknown spin id."}},
)
def get_spin(spin_id: str, container: Container = Depends(get_container)) -> SpinResponse:
    return container.spin.get_spin(spin_id)

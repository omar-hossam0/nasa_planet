"""Evidence receipt endpoints."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.core.dependencies import Container, get_container
from app.schemas.common import ErrorEnvelope
from app.schemas.receipt import ReceiptResponse

router = APIRouter(tags=["receipts"])


@router.get(
    "/receipts/{receipt_id}",
    response_model=ReceiptResponse,
    summary="Get an evidence receipt",
    description=(
        "Reproducibility metadata for a stored result: request parameters, AOI, period, dataset "
        "revisions, method version, mock provenance, warnings and a content hash."
    ),
    responses={404: {"model": ErrorEnvelope, "description": "Unknown receipt id."}},
)
def get_receipt(receipt_id: str, container: Container = Depends(get_container)) -> ReceiptResponse:
    return container.receipt.get_receipt(receipt_id)


@router.get(
    "/receipts/{receipt_id}/download",
    response_model=ReceiptResponse,
    summary="Download an evidence receipt as JSON",
    description=(
        "Returns the exact same receipt document as `GET /v1/receipts/{id}` with a "
        "`Content-Disposition: attachment` header. JSON only - no PDF generation."
    ),
    responses={404: {"model": ErrorEnvelope, "description": "Unknown receipt id."}},
)
def download_receipt(receipt_id: str, container: Container = Depends(get_container)) -> Response:
    receipt = container.receipt.get_receipt(receipt_id)
    payload = receipt.model_dump(mode="json")
    body = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=False)
    filename = f"{receipt.receipt_id}.json"
    return Response(
        content=body,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Receipt-Content-Hash": receipt.content_hash,
        },
    )

"""Evidence receipt construction and retrieval."""

from __future__ import annotations

import hashlib
import json

from app.core.exceptions import ReceiptNotFoundError
from app.repositories.interfaces import ReceiptRepository
from app.schemas.receipt import Provenance, ReceiptLinks, ReceiptResponse
from app.schemas.results import ResultResponse


def compute_content_hash(receipt: ReceiptResponse) -> str:
    """sha256 over the canonical receipt body (hash and links excluded)."""
    payload = receipt.model_dump(mode="json")
    payload.pop("content_hash", None)
    payload.pop("links", None)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_receipt(
    result: ResultResponse,
    *,
    receipt_id: str,
    registry_snapshot: str,
    api_prefix: str,
) -> ReceiptResponse:
    """Build the receipt that belongs to a stored result."""
    receipt = ReceiptResponse(
        receipt_id=receipt_id,
        result_id=result.result_id,
        job_id=result.job_id,
        analysis=result.analysis,
        variable_ids=result.analysis.variable_ids,
        region_id=result.analysis.region_id,
        aoi=result.analysis.aoi.canonical(),
        start_month=result.analysis.start_month,
        end_month=result.analysis.end_month,
        period_months=result.analysis.period_months,
        dataset_revisions=result.datasets,
        method=result.method,
        provenance=Provenance(registry_snapshot=registry_snapshot),
        warnings=result.warnings,
        generated_at=result.created_at,
        content_hash="",
        links=ReceiptLinks(
            self_url=f"{api_prefix}/receipts/{receipt_id}",
            download=f"{api_prefix}/receipts/{receipt_id}/download",
            result=f"{api_prefix}/results/{result.result_id}",
        ),
    )
    receipt.content_hash = compute_content_hash(receipt)
    return receipt


class ReceiptService:
    def __init__(self, receipts: ReceiptRepository) -> None:
        self._receipts = receipts

    def get_receipt(self, receipt_id: str) -> ReceiptResponse:
        receipt = self._receipts.get(receipt_id)
        if receipt is None:
            raise ReceiptNotFoundError(receipt_id)
        return receipt

    def get_by_result(self, result_id: str) -> ReceiptResponse:
        receipt = self._receipts.get_by_result(result_id)
        if receipt is None:
            raise ReceiptNotFoundError(f"receipt-for-{result_id}")
        return receipt

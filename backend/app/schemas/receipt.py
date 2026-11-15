"""Evidence receipt schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import DISCLAIMER, ApiWarning, DataMode
from app.schemas.results import AnalysisEcho, DatasetRevision, MethodRef


class Provenance(BaseModel):
    mode: str = "mock"
    generator: str = "trend-detective-backend"
    note: str = (
        "Mock provenance only. No NASA product revision, granule list or official "
        "citation is asserted by this receipt."
    )
    registry_snapshot: str
    statistics_adapter: str = "MockStatisticsAdapter"


class ReceiptLinks(BaseModel):
    self_url: str
    download: str
    result: str


class ReceiptResponse(BaseModel):
    receipt_id: str
    receipt_version: str = "1.0"
    result_id: str
    job_id: str
    data_mode: DataMode = DataMode.mock
    disclaimer: str = DISCLAIMER
    analysis: AnalysisEcho
    variable_ids: list[str]
    region_id: str
    aoi: list[float] = Field(description="[west, south, east, north] in WGS84 degrees.")
    start_month: str
    end_month: str
    period_months: int
    dataset_revisions: list[DatasetRevision]
    method: MethodRef
    provenance: Provenance
    warnings: list[ApiWarning] = Field(default_factory=list)
    generated_at: datetime
    content_hash: str = Field(description="sha256 of the canonical receipt body, excluding this field.")
    links: ReceiptLinks

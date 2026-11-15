"""Repository contracts.

Swapping these for SQLAlchemy implementations later must not change any router
or service signature. Records are the API schemas themselves in this milestone
because there is no separate persistence model to map yet.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from app.schemas.analysis import JobStatusResponse
from app.schemas.receipt import ReceiptResponse
from app.schemas.results import ResultResponse
from app.schemas.spin import SpinResponse


@dataclass(frozen=True)
class CacheEntry:
    """Maps a canonical request key onto the artefacts it produced."""

    cache_key: str
    job_id: str
    result_id: str
    receipt_id: str


@runtime_checkable
class JobRepository(Protocol):
    def add(self, job: JobStatusResponse) -> None: ...

    def get(self, job_id: str) -> JobStatusResponse | None: ...

    def replace(self, job: JobStatusResponse) -> None: ...

    def list_all(self) -> list[JobStatusResponse]: ...


@runtime_checkable
class ResultRepository(Protocol):
    def add(self, result: ResultResponse) -> None: ...

    def get(self, result_id: str) -> ResultResponse | None: ...

    def list_all(self) -> list[ResultResponse]: ...


@runtime_checkable
class ReceiptRepository(Protocol):
    def add(self, receipt: ReceiptResponse) -> None: ...

    def get(self, receipt_id: str) -> ReceiptResponse | None: ...

    def get_by_result(self, result_id: str) -> ReceiptResponse | None: ...


@runtime_checkable
class SpinRepository(Protocol):
    def add(self, spin: SpinResponse) -> None: ...

    def get(self, spin_id: str) -> SpinResponse | None: ...


@runtime_checkable
class AnalysisCacheRepository(Protocol):
    def get(self, cache_key: str) -> CacheEntry | None: ...

    def put(self, entry: CacheEntry) -> None: ...

    def clear(self) -> None: ...

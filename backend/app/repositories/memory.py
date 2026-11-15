"""Process-local in-memory repositories.

LIMITATIONS (documented in the README and docs/MOCK_DATA.md):
* state is lost when the process exits;
* state is per-process, so multiple uvicorn workers do NOT share it;
* there is no eviction, so memory grows with the number of analyses.

They exist to unblock API development, not to provide durability.
"""

from __future__ import annotations

from threading import RLock
from typing import Generic, TypeVar

from app.repositories.interfaces import CacheEntry
from app.schemas.analysis import JobStatusResponse
from app.schemas.receipt import ReceiptResponse
from app.schemas.results import ResultResponse
from app.schemas.spin import SpinResponse

T = TypeVar("T")


class _MemoryStore(Generic[T]):
    """Small thread-safe dict wrapper. Not durable, not distributed."""

    def __init__(self) -> None:
        self._items: dict[str, T] = {}
        self._lock = RLock()

    def put(self, key: str, item: T) -> None:
        with self._lock:
            self._items[key] = item

    def get(self, key: str) -> T | None:
        with self._lock:
            return self._items.get(key)

    def all(self) -> list[T]:
        with self._lock:
            return list(self._items.values())

    def clear(self) -> None:
        with self._lock:
            self._items.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._items)


class InMemoryJobRepository:
    def __init__(self) -> None:
        self._store: _MemoryStore[JobStatusResponse] = _MemoryStore()

    def add(self, job: JobStatusResponse) -> None:
        self._store.put(job.job_id, job)

    def get(self, job_id: str) -> JobStatusResponse | None:
        return self._store.get(job_id)

    def replace(self, job: JobStatusResponse) -> None:
        self._store.put(job.job_id, job)

    def list_all(self) -> list[JobStatusResponse]:
        return self._store.all()

    def clear(self) -> None:
        self._store.clear()


class InMemoryResultRepository:
    def __init__(self) -> None:
        self._store: _MemoryStore[ResultResponse] = _MemoryStore()

    def add(self, result: ResultResponse) -> None:
        self._store.put(result.result_id, result)

    def get(self, result_id: str) -> ResultResponse | None:
        return self._store.get(result_id)

    def list_all(self) -> list[ResultResponse]:
        return self._store.all()

    def clear(self) -> None:
        self._store.clear()


class InMemoryReceiptRepository:
    def __init__(self) -> None:
        self._store: _MemoryStore[ReceiptResponse] = _MemoryStore()

    def add(self, receipt: ReceiptResponse) -> None:
        self._store.put(receipt.receipt_id, receipt)

    def get(self, receipt_id: str) -> ReceiptResponse | None:
        return self._store.get(receipt_id)

    def get_by_result(self, result_id: str) -> ReceiptResponse | None:
        for receipt in self._store.all():
            if receipt.result_id == result_id:
                return receipt
        return None

    def clear(self) -> None:
        self._store.clear()


class InMemorySpinRepository:
    def __init__(self) -> None:
        self._store: _MemoryStore[SpinResponse] = _MemoryStore()

    def add(self, spin: SpinResponse) -> None:
        self._store.put(spin.spin_id, spin)

    def get(self, spin_id: str) -> SpinResponse | None:
        return self._store.get(spin_id)

    def clear(self) -> None:
        self._store.clear()


class InMemoryAnalysisCacheRepository:
    def __init__(self) -> None:
        self._store: _MemoryStore[CacheEntry] = _MemoryStore()

    def get(self, cache_key: str) -> CacheEntry | None:
        return self._store.get(cache_key)

    def put(self, entry: CacheEntry) -> None:
        self._store.put(entry.cache_key, entry)

    def clear(self) -> None:
        self._store.clear()

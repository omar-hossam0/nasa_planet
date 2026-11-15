"""Deterministic in-process job manager.

No Celery, no Redis, no background threads. A submitted unit of work runs
immediately by default so the API is pollable straight after ``POST``.

Setting ``mock_auto_complete_jobs=false`` keeps jobs in ``queued`` until
``run_pending()`` is called, which lets tests observe the full
``queued -> running -> completed`` transition without sleeping.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)

WorkUnit = Callable[[], str]


@dataclass
class _PendingJob:
    job_id: str
    work: WorkUnit


class MockJobManager:
    def __init__(self, *, auto_complete: bool = True) -> None:
        self._auto_complete = auto_complete
        self._pending: dict[str, _PendingJob] = {}

    @property
    def auto_complete(self) -> bool:
        return self._auto_complete

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    def submit(self, job_id: str, work: WorkUnit) -> str | None:
        """Run ``work`` now, or queue it. Returns the result id when it ran."""
        if self._auto_complete:
            logger.info("job %s executing inline", job_id)
            return work()
        self._pending[job_id] = _PendingJob(job_id=job_id, work=work)
        logger.info("job %s queued (auto_complete disabled)", job_id)
        return None

    def run_pending(self) -> list[str]:
        """Execute every queued job in submission order. Returns job ids run."""
        executed: list[str] = []
        for job_id in list(self._pending):
            pending = self._pending.pop(job_id)
            pending.work()
            executed.append(job_id)
        return executed

    def run_job(self, job_id: str) -> str | None:
        """Execute one specific queued job, if present."""
        pending = self._pending.pop(job_id, None)
        if pending is None:
            return None
        return pending.work()

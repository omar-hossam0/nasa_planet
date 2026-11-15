"""Background job worker.

A single background thread claims queued jobs from SQLite and runs the frozen
analysis pipeline. Jobs interrupted by a crash are never assumed successful:
they are marked retryable failures at startup.
"""
from __future__ import annotations

import json
import threading
import time
import traceback

from . import analysis_runner, canonical, config, db

_STOP = threading.Event()
_THREAD: threading.Thread | None = None


def process_one() -> bool:
    """Claim and run a single job. Returns True if a job was processed."""
    job = db.claim_next_job()
    if not job:
        return False
    try:
        payload, receipt_payload, result_id, receipt_id = \
            analysis_runner.run(job)
        payload_sha = canonical.sha256_bytes(
            json.dumps(payload, sort_keys=True).encode("utf-8"))
        receipt_sha = canonical.sha256_bytes(
            json.dumps(receipt_payload, sort_keys=True).encode("utf-8"))
        db.save_result_and_receipt(job, payload, payload_sha, receipt_payload,
                                   receipt_sha, result_id, receipt_id)
        db.finish_job(job["id"], "succeeded", result_id=result_id)
    except analysis_runner.AnalysisError as exc:
        db.finish_job(job["id"], "failed", exc.code, exc.detail)
    except Exception as exc:  # never leak a stack trace to the client
        db.finish_job(job["id"], "failed", "INTERNAL_ERROR",
                      f"{type(exc).__name__}: {str(exc)[:300]}")
        traceback.print_exc()
    return True


def _loop() -> None:
    while not _STOP.is_set():
        try:
            worked = process_one()
        except Exception:  # keep the worker alive
            traceback.print_exc()
            worked = False
        if not worked:
            _STOP.wait(config.WORKER_POLL_SECONDS)


def start() -> None:
    global _THREAD
    if _THREAD and _THREAD.is_alive():
        return
    _STOP.clear()
    _THREAD = threading.Thread(target=_loop, name="td-worker", daemon=True)
    _THREAD.start()


def stop(timeout: float = 5.0) -> None:
    _STOP.set()
    if _THREAD:
        _THREAD.join(timeout=timeout)

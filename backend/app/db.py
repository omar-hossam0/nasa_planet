"""SQLite persistence: jobs, results, receipts, catalog snapshot.

Rules enforced here:
- one job per canonical request hash (unique constraint),
- a result can only be written for a job that actually succeeded,
- a receipt is written only after a result exists,
- stale 'running' jobs are marked retryable failures on startup.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from . import config

_LOCK = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    request_hash TEXT NOT NULL UNIQUE,
    canonical_request_json TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('queued','running','succeeded','failed')),
    progress REAL NOT NULL DEFAULT 0,
    attempts INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    error_code TEXT,
    error_detail TEXT,
    result_id TEXT,
    data_revision TEXT NOT NULL,
    method_revision TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS results (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL UNIQUE,
    request_hash TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL,
    receipt_id TEXT,
    created_at TEXT NOT NULL,
    data_revision TEXT NOT NULL,
    method_revision TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS receipts (
    id TEXT PRIMARY KEY,
    result_id TEXT NOT NULL UNIQUE,
    payload_json TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS catalog_entries (
    variable_id TEXT NOT NULL,
    region_id TEXT NOT NULL,
    data_revision TEXT NOT NULL,
    product_id TEXT NOT NULL,
    units TEXT NOT NULL,
    measurement_ready INTEGER NOT NULL,
    method_ready INTEGER NOT NULL,
    app_available INTEGER NOT NULL,
    manifest_path TEXT NOT NULL,
    PRIMARY KEY (variable_id, region_id, data_revision)
);
CREATE INDEX IF NOT EXISTS idx_jobs_state ON jobs(state, created_at);
CREATE INDEX IF NOT EXISTS idx_results_hash ON results(request_hash, data_revision, method_revision);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    config.ensure_dirs()
    con = sqlite3.connect(str(config.DB_PATH), timeout=30,
                          check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    return con


def init_db(path: Path | None = None) -> None:
    with _LOCK:
        con = connect()
        try:
            con.executescript(SCHEMA)
            con.commit()
        finally:
            con.close()


# ---------------------------------------------------------------- jobs

def insert_job(canonical: dict, request_hash: str, data_revision: str,
               method_revision: str) -> tuple[dict, bool]:
    """Insert a job or return the existing one. Returns (job, created)."""
    with _LOCK:
        con = connect()
        try:
            existing = con.execute(
                "SELECT * FROM jobs WHERE request_hash=?", (request_hash,)
            ).fetchone()
            if existing:
                if existing["state"] == "failed":
                    # a failed job is retryable: requeue it instead of handing
                    # back a permanent failure for the same canonical request.
                    # Any stale artifacts from an earlier attempt are removed
                    # first, because a retried job must not inherit them.
                    con.execute(
                        "DELETE FROM receipts WHERE result_id IN "
                        "(SELECT id FROM results WHERE job_id=?)",
                        (existing["id"],))
                    con.execute("DELETE FROM results WHERE job_id=?",
                                (existing["id"],))
                    con.execute(
                        "UPDATE jobs SET state='queued', progress=0, "
                        "started_at=NULL, finished_at=NULL, error_code=NULL, "
                        "error_detail=NULL, result_id=NULL WHERE id=?",
                        (existing["id"],))
                    con.commit()
                    row = con.execute("SELECT * FROM jobs WHERE id=?",
                                      (existing["id"],)).fetchone()
                    return dict(row), False
                return dict(existing), False
            job_id = "job_" + uuid.uuid4().hex[:16]
            con.execute(
                "INSERT INTO jobs (id, request_hash, canonical_request_json, "
                "state, progress, attempts, created_at, data_revision, "
                "method_revision) VALUES (?,?,?,'queued',0,0,?,?,?)",
                (job_id, request_hash,
                 json.dumps(canonical, sort_keys=True), now(),
                 data_revision, method_revision))
            con.commit()
            row = con.execute("SELECT * FROM jobs WHERE id=?",
                              (job_id,)).fetchone()
            return dict(row), True
        finally:
            con.close()


def get_job(job_id: str) -> dict | None:
    con = connect()
    try:
        row = con.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        return dict(row) if row else None
    finally:
        con.close()


def claim_next_job() -> dict | None:
    """Transactionally move one queued job to running.

    Retries briefly on a transient lock instead of killing the worker.
    """
    for attempt in range(4):
        try:
            return _claim_next_job_once()
        except sqlite3.OperationalError:
            if attempt == 3:
                raise
            time.sleep(0.4 * (attempt + 1))
    return None


def _claim_next_job_once() -> dict | None:
    with _LOCK:
        con = connect()
        try:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute(
                "SELECT id FROM jobs WHERE state='queued' "
                "ORDER BY created_at LIMIT 1").fetchone()
            if not row:
                con.commit()
                return None
            job_id = row["id"]
            cur = con.execute(
                "UPDATE jobs SET state='running', started_at=?, "
                "progress=0.05, attempts=attempts+1 "
                "WHERE id=? AND state='queued'", (now(), job_id))
            con.commit()
            if cur.rowcount != 1:
                return None
            job = con.execute("SELECT * FROM jobs WHERE id=?",
                              (job_id,)).fetchone()
            return dict(job)
        finally:
            con.close()


def finish_job(job_id: str, state: str, error_code: str | None = None,
               error_detail: str | None = None,
               result_id: str | None = None) -> None:
    assert state in ("succeeded", "failed")
    with _LOCK:
        con = connect()
        try:
            con.execute(
                "UPDATE jobs SET state=?, finished_at=?, progress=1.0, "
                "error_code=?, error_detail=?, result_id=? WHERE id=?",
                (state, now(), error_code, error_detail, result_id, job_id))
            con.commit()
        finally:
            con.close()


def recover_stale_jobs() -> int:
    """Any 'running' job at startup was interrupted; never assume success."""
    with _LOCK:
        con = connect()
        try:
            cur = con.execute(
                "UPDATE jobs SET state='failed', finished_at=?, "
                "error_code='INTERRUPTED', "
                "error_detail='worker stopped before the job finished; "
                "resubmit to retry' WHERE state='running'", (now(),))
            con.commit()
            return cur.rowcount
        finally:
            con.close()


# ------------------------------------------------------------- results

def save_result_and_receipt(job: dict, payload: dict, payload_sha256: str,
                           receipt_payload: dict, receipt_sha256: str,
                           result_id: str, receipt_id: str) -> None:
    """Write the result and its receipt in one transaction.

    Either both exist or neither does, so a receipt can never be issued for a
    job that has no stored result.
    """
    with _LOCK:
        con = connect()
        try:
            con.execute("BEGIN IMMEDIATE")
            con.execute(
                "INSERT INTO results (id, job_id, request_hash, payload_json, "
                "payload_sha256, receipt_id, created_at, data_revision, "
                "method_revision) VALUES (?,?,?,?,?,?,?,?,?)",
                (result_id, job["id"], job["request_hash"],
                 json.dumps(payload, sort_keys=True), payload_sha256,
                 receipt_id, now(), job["data_revision"],
                 job["method_revision"]))
            con.execute(
                "INSERT INTO receipts (id, result_id, payload_json, "
                "payload_sha256, created_at) VALUES (?,?,?,?,?)",
                (receipt_id, result_id,
                 json.dumps(receipt_payload, sort_keys=True),
                 receipt_sha256, now()))
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()


def get_result_by_job(job_id: str) -> dict | None:
    con = connect()
    try:
        row = con.execute("SELECT * FROM results WHERE job_id=?",
                          (job_id,)).fetchone()
        return dict(row) if row else None
    finally:
        con.close()


def find_cached_result(request_hash: str, data_revision: str,
                       method_revision: str) -> dict | None:
    con = connect()
    try:
        row = con.execute(
            "SELECT r.*, j.id AS job_id FROM results r JOIN jobs j "
            "ON j.id = r.job_id WHERE r.request_hash=? AND "
            "r.data_revision=? AND r.method_revision=? AND j.state='succeeded'",
            (request_hash, data_revision, method_revision)).fetchone()
        return dict(row) if row else None
    finally:
        con.close()


# ------------------------------------------------------------ receipts

def get_receipt(receipt_id: str) -> dict | None:
    con = connect()
    try:
        row = con.execute("SELECT * FROM receipts WHERE id=?",
                          (receipt_id,)).fetchone()
        return dict(row) if row else None
    finally:
        con.close()


# ------------------------------------------------------------- catalog

def sync_catalog(entries: list[dict], data_revision: str) -> int:
    with _LOCK:
        con = connect()
        try:
            con.execute("DELETE FROM catalog_entries WHERE data_revision=?",
                        (data_revision,))
            con.executemany(
                "INSERT OR REPLACE INTO catalog_entries (variable_id, "
                "region_id, data_revision, product_id, units, "
                "measurement_ready, method_ready, app_available, "
                "manifest_path) VALUES (?,?,?,?,?,?,?,?,?)",
                [(e["variable_id"], e["region_id"], data_revision,
                  e["product_id"], e["units"], int(e["measurement_ready"]),
                  int(e["method_ready"]), int(e["app_available"]),
                  e["manifest_path"]) for e in entries])
            con.commit()
            return len(entries)
        finally:
            con.close()


def catalog_rows(data_revision: str) -> list[dict]:
    con = connect()
    try:
        rows = con.execute(
            "SELECT * FROM catalog_entries WHERE data_revision=? "
            "ORDER BY variable_id, region_id", (data_revision,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()

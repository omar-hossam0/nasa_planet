"""Application error taxonomy.

Every error surfaced by the API is an :class:`AppError` with a stable machine
readable ``code``. Routers never raise bare ``HTTPException`` so that clients
can rely on a single error envelope.
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class ErrorCode(str, Enum):
    """Stable error codes. Clients may branch on these values."""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    VARIABLE_NOT_FOUND = "VARIABLE_NOT_FOUND"
    REGION_NOT_FOUND = "REGION_NOT_FOUND"
    JOB_NOT_FOUND = "JOB_NOT_FOUND"
    RESULT_NOT_FOUND = "RESULT_NOT_FOUND"
    CELL_NOT_FOUND = "CELL_NOT_FOUND"
    RECEIPT_NOT_FOUND = "RECEIPT_NOT_FOUND"
    SPIN_NOT_FOUND = "SPIN_NOT_FOUND"
    INVALID_AOI = "INVALID_AOI"
    INVALID_PERIOD = "INVALID_PERIOD"
    DATA_NOT_AVAILABLE = "DATA_NOT_AVAILABLE"
    RESULT_NOT_COMPLETE = "RESULT_NOT_COMPLETE"
    INCOMPATIBLE_COMPARISON = "INCOMPATIBLE_COMPARISON"
    INVALID_SPIN_WINDOW = "INVALID_SPIN_WINDOW"
    UNSUPPORTED_LANGUAGE = "UNSUPPORTED_LANGUAGE"
    UNSUPPORTED_AGGREGATION_POLICY = "UNSUPPORTED_AGGREGATION_POLICY"
    MOCK_MODE_DISABLED = "MOCK_MODE_DISABLED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class AppError(Exception):
    """Base class for all handled application errors."""

    code: ErrorCode = ErrorCode.INTERNAL_ERROR
    status_code: int = 500
    message: str = "An unexpected error occurred."

    def __init__(
        self,
        message: str | None = None,
        *,
        details: dict[str, Any] | None = None,
        code: ErrorCode | None = None,
        status_code: int | None = None,
    ) -> None:
        self.message = message or self.message
        self.details = details or {}
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        super().__init__(self.message)


# ---------------------------------------------------------------------------
# 404 family
# ---------------------------------------------------------------------------
class NotFoundError(AppError):
    code = ErrorCode.RESULT_NOT_FOUND
    status_code = 404


class VariableNotFoundError(NotFoundError):
    code = ErrorCode.VARIABLE_NOT_FOUND

    def __init__(self, variable_id: str, *, known: list[str] | None = None) -> None:
        super().__init__(
            f"Unknown variable_id '{variable_id}'.",
            details={"variable_id": variable_id, "known_variable_ids": known or []},
        )


class RegionNotFoundError(NotFoundError):
    code = ErrorCode.REGION_NOT_FOUND

    def __init__(self, region_id: str, *, known: list[str] | None = None) -> None:
        super().__init__(
            f"Unknown region_id '{region_id}'.",
            details={"region_id": region_id, "known_region_ids": known or []},
        )


class JobNotFoundError(NotFoundError):
    code = ErrorCode.JOB_NOT_FOUND

    def __init__(self, job_id: str) -> None:
        super().__init__(f"Analysis job '{job_id}' was not found.", details={"job_id": job_id})


class ResultNotFoundError(NotFoundError):
    code = ErrorCode.RESULT_NOT_FOUND

    def __init__(self, result_id: str) -> None:
        super().__init__(f"Result '{result_id}' was not found.", details={"result_id": result_id})


class CellNotFoundError(NotFoundError):
    code = ErrorCode.CELL_NOT_FOUND

    def __init__(self, cell_id: str, result_id: str) -> None:
        super().__init__(
            f"Cell '{cell_id}' does not belong to result '{result_id}'.",
            details={"cell_id": cell_id, "result_id": result_id},
        )


class ReceiptNotFoundError(NotFoundError):
    code = ErrorCode.RECEIPT_NOT_FOUND

    def __init__(self, receipt_id: str) -> None:
        super().__init__(f"Receipt '{receipt_id}' was not found.", details={"receipt_id": receipt_id})


class SpinNotFoundError(NotFoundError):
    code = ErrorCode.SPIN_NOT_FOUND

    def __init__(self, spin_id: str) -> None:
        super().__init__(f"Spin It operation '{spin_id}' was not found.", details={"spin_id": spin_id})


# ---------------------------------------------------------------------------
# 422 family
# ---------------------------------------------------------------------------
class RequestValidationAppError(AppError):
    code = ErrorCode.VALIDATION_ERROR
    status_code = 422


class InvalidAoiError(RequestValidationAppError):
    code = ErrorCode.INVALID_AOI

    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(message, details=details or None)


class InvalidPeriodError(RequestValidationAppError):
    code = ErrorCode.INVALID_PERIOD

    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(message, details=details or None)


class InvalidSpinWindowError(RequestValidationAppError):
    code = ErrorCode.INVALID_SPIN_WINDOW

    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(message, details=details or None)


class UnsupportedLanguageError(RequestValidationAppError):
    code = ErrorCode.UNSUPPORTED_LANGUAGE

    def __init__(self, language: str, supported: list[str]) -> None:
        super().__init__(
            f"Language '{language}' is not supported.",
            details={"language": language, "supported_languages": supported},
        )


class UnsupportedAggregationPolicyError(RequestValidationAppError):
    code = ErrorCode.UNSUPPORTED_AGGREGATION_POLICY

    def __init__(self, policy: str, supported: list[str]) -> None:
        super().__init__(
            f"Aggregation policy '{policy}' is not supported by the current method contract.",
            details={"aggregation_policy": policy, "supported_policies": supported},
        )


# ---------------------------------------------------------------------------
# 409 family
# ---------------------------------------------------------------------------
class ConflictError(AppError):
    code = ErrorCode.DATA_NOT_AVAILABLE
    status_code = 409


class DataNotAvailableError(ConflictError):
    code = ErrorCode.DATA_NOT_AVAILABLE

    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(message, details=details or None)


class ResultNotCompleteError(ConflictError):
    code = ErrorCode.RESULT_NOT_COMPLETE

    def __init__(self, job_id: str, status: str) -> None:
        super().__init__(
            f"Analysis job '{job_id}' is not complete (status='{status}'); no result is available yet.",
            details={"job_id": job_id, "status": status},
        )


class IncompatibleComparisonError(ConflictError):
    code = ErrorCode.INCOMPATIBLE_COMPARISON

    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(message, details=details or None)


# ---------------------------------------------------------------------------
# 503 family
# ---------------------------------------------------------------------------
class UnavailableError(AppError):
    code = ErrorCode.MOCK_MODE_DISABLED
    status_code = 503


class MockModeDisabledError(UnavailableError):
    code = ErrorCode.MOCK_MODE_DISABLED

    def __init__(self, capability: str) -> None:
        super().__init__(
            f"'{capability}' is only available while MOCK_MODE is enabled. "
            "The real integration has not been delivered yet.",
            details={"capability": capability},
        )

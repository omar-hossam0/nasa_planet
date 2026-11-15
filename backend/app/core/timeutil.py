"""Month-granularity helpers.

The whole API speaks ``YYYY-MM`` strings; these helpers convert to a sortable
integer index so date arithmetic stays trivial and testable.
"""

from __future__ import annotations

import re

MONTH_PATTERN = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")


def is_valid_month(value: str) -> bool:
    return bool(MONTH_PATTERN.match(value))


def month_to_index(value: str) -> int:
    """``2005-03`` -> ``2005 * 12 + 2`` (zero-based month)."""
    match = MONTH_PATTERN.match(value)
    if not match:
        raise ValueError(f"'{value}' is not a valid YYYY-MM month.")
    return int(match.group(1)) * 12 + (int(match.group(2)) - 1)


def index_to_month(index: int) -> str:
    year, month = divmod(index, 12)
    return f"{year:04d}-{month + 1:02d}"


def month_range(start_month: str, end_month: str) -> list[str]:
    """Inclusive list of months between two ``YYYY-MM`` values."""
    start = month_to_index(start_month)
    end = month_to_index(end_month)
    if end < start:
        raise ValueError("end_month precedes start_month")
    return [index_to_month(index) for index in range(start, end + 1)]


def month_count(start_month: str, end_month: str) -> int:
    return month_to_index(end_month) - month_to_index(start_month) + 1


def year_of(value: str) -> int:
    return int(value[:4])


def month_of(value: str) -> int:
    return int(value[5:7])

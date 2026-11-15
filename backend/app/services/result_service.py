"""Completed-result retrieval."""

from __future__ import annotations

from app.core.exceptions import ResultNotFoundError
from app.repositories.interfaces import ResultRepository
from app.schemas.results import ResultResponse


class ResultService:
    def __init__(self, results: ResultRepository) -> None:
        self._results = results

    def get_result(self, result_id: str) -> ResultResponse:
        result = self._results.get(result_id)
        if result is None:
            raise ResultNotFoundError(result_id)
        return result

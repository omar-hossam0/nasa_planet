"""Spin It: time-window sensitivity on top of a completed result."""

from __future__ import annotations

import hashlib

from app.adapters.interfaces import NASADataAdapter, StatisticsAdapter
from app.core.config import Settings
from app.core.exceptions import InvalidSpinWindowError, SpinNotFoundError
from app.repositories.interfaces import SpinRepository
from app.schemas.spin import (
    SpinCreateResponse,
    SpinLinks,
    SpinRequest,
    SpinResponse,
    SpinStatus,
)
from app.services.analysis_service import spec_from_result
from app.services.result_service import ResultService


class SpinService:
    def __init__(
        self,
        *,
        results: ResultService,
        spins: SpinRepository,
        statistics: StatisticsAdapter,
        data: NASADataAdapter,
        settings: Settings,
    ) -> None:
        self._results = results
        self._spins = spins
        self._statistics = statistics
        self._data = data
        self._settings = settings

    def create_spin(self, result_id: str, request: SpinRequest) -> SpinCreateResponse:
        result = self._results.get_result(result_id)
        spec = spec_from_result(result, self._data)

        self._validate_window(spec.start_month, spec.end_month, request)

        computed = self._statistics.compute_spin(spec, result_id=result.result_id, request=request)
        primary = result.variables[0]
        trend_unit = primary.trend.slope_unit or f"{primary.unit} year-1"

        spin_id = "spin_mock_" + hashlib.sha256(
            "|".join(
                [
                    result.result_id,
                    str(request.minimum_window_years),
                    str(request.start_year_min),
                    str(request.end_year_max),
                ]
            ).encode("utf-8")
        ).hexdigest()[:8]

        spin = SpinResponse(
            spin_id=spin_id,
            result_id=result.result_id,
            status=SpinStatus.completed,
            request=request,
            variable_id=primary.variable_id,
            display_name=primary.display_name,
            unit=primary.unit,
            trend_unit=trend_unit,
            windows=computed.windows,
            summary=computed.summary,
            warnings=[
                "Spin It does not modify the parent result; it reports separate synthetic windows.",
                *[warning.message for warning in computed.warnings],
            ],
        )
        self._spins.add(spin)

        prefix = self._settings.api_prefix
        return SpinCreateResponse(
            spin_id=spin_id,
            result_id=result.result_id,
            status=SpinStatus.completed,
            message=(
                f"Spin It computed {len(computed.windows)} deterministic mock window(s). "
                "The parent result was not modified."
            ),
            links=SpinLinks(
                self_url=f"{prefix}/spin/{spin_id}",
                result=f"{prefix}/results/{result.result_id}",
            ),
        )

    def get_spin(self, spin_id: str) -> SpinResponse:
        spin = self._spins.get(spin_id)
        if spin is None:
            raise SpinNotFoundError(spin_id)
        return spin

    # -- validation -------------------------------------------------------
    def _validate_window(self, start_month: str, end_month: str, request: SpinRequest) -> None:
        coverage_start_year = int(start_month[:4])
        coverage_end_year = int(end_month[:4])
        total_years = coverage_end_year - coverage_start_year + 1

        if request.minimum_window_years < 1:
            raise InvalidSpinWindowError("minimum_window_years must be positive.")

        if request.minimum_window_years > total_years:
            raise InvalidSpinWindowError(
                "minimum_window_years exceeds the covered period of the base result.",
                minimum_window_years=request.minimum_window_years,
                covered_years=total_years,
            )

        if request.start_year_min is not None and request.start_year_min < coverage_start_year:
            raise InvalidSpinWindowError(
                "start_year_min is before the base result coverage.",
                start_year_min=request.start_year_min,
                coverage=[coverage_start_year, coverage_end_year],
            )
        if request.end_year_max is not None and request.end_year_max > coverage_end_year:
            raise InvalidSpinWindowError(
                "end_year_max is after the base result coverage.",
                end_year_max=request.end_year_max,
                coverage=[coverage_start_year, coverage_end_year],
            )

        lower = request.start_year_min or coverage_start_year
        upper = request.end_year_max or coverage_end_year
        if lower > upper:
            raise InvalidSpinWindowError(
                "start_year_min must not be greater than end_year_max.",
                start_year_min=lower,
                end_year_max=upper,
            )

        window_count = (upper - request.minimum_window_years) - lower + 1
        if window_count <= 0:
            raise InvalidSpinWindowError(
                "The requested window does not fit inside the selected years.",
                minimum_window_years=request.minimum_window_years,
                years=[lower, upper],
            )
        if window_count > self._settings.max_spin_windows:
            raise InvalidSpinWindowError(
                f"At most {self._settings.max_spin_windows} windows may be requested.",
                requested_windows=window_count,
                max_windows=self._settings.max_spin_windows,
            )

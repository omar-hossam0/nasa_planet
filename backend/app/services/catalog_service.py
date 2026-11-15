"""Catalog, region and availability business logic."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.adapters.interfaces import NASADataAdapter
from app.core.config import Settings
from app.core.exceptions import (
    InvalidAoiError,
    InvalidPeriodError,
    RegionNotFoundError,
    VariableNotFoundError,
)
from app.core.timeutil import is_valid_month, month_to_index
from app.mocks.catalog import RegionRecord, VariableRecord
from app.schemas.catalog import (
    AvailabilityReason,
    AvailabilityResponse,
    CatalogResponse,
    CatalogState,
    RegionSummary,
    RegionsResponse,
    SourceInfo,
    VariableDetail,
    VariableSummary,
)
from app.schemas.common import AggregationPolicy, Aoi, DataMode

SUPPORTED_AGGREGATION_POLICIES: tuple[AggregationPolicy, ...] = (
    AggregationPolicy.area_weighted,
    AggregationPolicy.cell_mean,
)

@dataclass(frozen=True)
class AvailabilityEvaluation:
    usable: bool
    reason_code: AvailabilityReason
    message: str
    details: dict = field(default_factory=dict)


def evaluate_demo_availability(
    data: NASADataAdapter,
    *,
    variable_id: str,
    region_id: str,
    start_month: str,
    end_month: str,
    aoi: Aoi | None,
) -> AvailabilityEvaluation:
    """Single source of truth for "can the demo run this?".

    Used by both ``/catalog/availability`` and ``POST /analyses`` so the two can
    never disagree.
    """
    record = data.get_variable(variable_id)
    if record is None:
        return AvailabilityEvaluation(
            usable=False,
            reason_code=AvailabilityReason.UNKNOWN_VARIABLE,
            message=f"Variable '{variable_id}' is not in the catalog.",
            details={"variable_id": variable_id},
        )

    # Defensive: the router validates the format, but a service caller must not
    # be able to trigger an unhandled ValueError.
    if not is_valid_month(start_month) or not is_valid_month(end_month):
        return AvailabilityEvaluation(
            usable=False,
            reason_code=AvailabilityReason.INVALID_PERIOD,
            message="Months must use the YYYY-MM format.",
            details={"start_month": start_month, "end_month": end_month},
        )

    region = data.get_region(region_id)
    if region is None:
        return AvailabilityEvaluation(
            usable=False,
            reason_code=AvailabilityReason.UNKNOWN_REGION,
            message=f"Region '{region_id}' is not configured.",
            details={"region_id": region_id},
        )

    if month_to_index(start_month) > month_to_index(end_month):
        return AvailabilityEvaluation(
            usable=False,
            reason_code=AvailabilityReason.INVALID_PERIOD,
            message="start_month must not be later than end_month.",
            details={"start_month": start_month, "end_month": end_month},
        )

    if region_id not in data.supported_region_ids(variable_id):
        return AvailabilityEvaluation(usable=False, reason_code=AvailabilityReason.OUTSIDE_COVERAGE,
            message='This variable is not available in the selected region.')

    if start_month < region.period_start or end_month > region.period_end:
        return AvailabilityEvaluation(usable=False, reason_code=AvailabilityReason.OUTSIDE_COVERAGE,
            message='The requested period is outside this region coverage.')

    if start_month < record.coverage_start or end_month > record.coverage_end:
        return AvailabilityEvaluation(
            usable=False,
            reason_code=AvailabilityReason.OUTSIDE_COVERAGE,
            message=(
                f"The requested period is outside the declared coverage "
                f"{record.coverage_start}..{record.coverage_end}."
            ),
            details={
                "requested": [start_month, end_month],
                "coverage": [record.coverage_start, record.coverage_end],
            },
        )

    if aoi is not None:
        west, south, east, north = region.bbox
        inside = (
            aoi.west >= west
            and aoi.east <= east
            and aoi.south >= south
            and aoi.north <= north
        )
        if not inside:
            return AvailabilityEvaluation(
                usable=False,
                reason_code=AvailabilityReason.OUTSIDE_COVERAGE,
                message="The AOI is not contained in the configured region bbox.",
                details={"aoi": aoi.canonical(), "region_bbox": list(region.bbox)},
            )

    if hasattr(data, 'ensure_available'):
        from types import SimpleNamespace
        from app.core.exceptions import DataNotAvailableError
        try:
            data.ensure_available(SimpleNamespace(variable_ids=[variable_id],region_id=region_id,
                start_month=start_month,end_month=end_month,
                aoi=aoi or Aoi(type='bbox',coordinates=list(region.bbox)),aggregation_policy=AggregationPolicy.area_weighted))
        except DataNotAvailableError as error:
            return AvailabilityEvaluation(usable=False,reason_code=AvailabilityReason.OUTSIDE_COVERAGE,message=error.message)

    return AvailabilityEvaluation(
        usable=True,
        reason_code=AvailabilityReason.MOCK_DEMO_ONLY,
        message=(
            "Usable for the mock demonstration only. The verified registry still reports "
            "method_ready=false and app_available=false."
        ),
        details={},
    )


class CatalogService:
    def __init__(self, data: NASADataAdapter, settings: Settings) -> None:
        self._data = data
        self._settings = settings

    # -- variables --------------------------------------------------------
    def list_variables(self) -> CatalogResponse:
        variables = [self._to_summary(record) for record in self._data.list_variables()]
        return CatalogResponse(
            variables=variables,
            count=len(variables),
            data_mode=DataMode.mock if self._settings.mock_mode else DataMode.real,
            disclaimer='Synthetic demonstration data. Not a NASA scientific result.' if self._settings.mock_mode else 'Real NASA inputs; descriptive analysis only. Inference is not released.',
            registry_snapshot=self._data.registry_snapshot(),
            warnings=[
                "Catalog metadata mirrors a repository snapshot, not a live NASA registry.",
                'app_available refers to the configured execution mode; descriptive availability does not release inference.',
            ],
        )

    def get_variable(self, variable_id: str) -> VariableDetail:
        resolved = self._data.resolve_variable_id(variable_id)
        record = self._data.get_variable(resolved) if resolved else None
        if record is None:
            raise VariableNotFoundError(variable_id, known=self._known_variable_ids())
        return self._to_detail(record)

    def list_regions(self) -> RegionsResponse:
        regions = [self._to_region(record) for record in self._data.list_regions()]
        return RegionsResponse(regions=regions, count=len(regions), data_mode='mock' if self._settings.mock_mode else 'real',
            disclaimer='Synthetic demonstration data.' if self._settings.mock_mode else 'Registered source coverage; descriptive analysis only.')

    # -- availability -----------------------------------------------------
    def check_availability(
        self,
        *,
        variable_id: str,
        region_id: str,
        start_month: str,
        end_month: str,
        bbox: str | None = None,
    ) -> AvailabilityResponse:
        resolved_variable = self._data.resolve_variable_id(variable_id)
        if resolved_variable is None:
            raise VariableNotFoundError(variable_id, known=self._known_variable_ids())
        resolved_region = self._data.resolve_region_id(region_id)
        if resolved_region is None:
            raise RegionNotFoundError(region_id, known=self._known_region_ids())

        aoi = self._parse_bbox(bbox) if bbox else None
        record = self._data.get_variable(resolved_variable)
        assert record is not None  # resolved above

        evaluation = evaluate_demo_availability(
            self._data,
            variable_id=resolved_variable,
            region_id=resolved_region,
            start_month=start_month,
            end_month=end_month,
            aoi=aoi,
        )

        warnings = [
            "Availability is mock-simulated. measurement_ready/method_ready/app_available "
            "are copied from the verified registry snapshot; demo_available is the mock gate."
        ] if self._settings.mock_mode else ['Actual source coverage and native cell centres checked. Descriptive-only processing; inference withheld.']
        if not record.units_verified:
            warnings.append(f"Unit '{record.unit}' for {resolved_variable} is unverified.")

        return AvailabilityResponse(
            variable_id=resolved_variable,
            region_id=resolved_region,
            start_month=start_month,
            end_month=end_month,
            aoi=aoi,
            measurement_ready=record.measurement_ready,
            method_ready=record.method_ready,
            app_available=record.app_available,
            demo_available=evaluation.usable if self._settings.mock_mode else False,
            usable=evaluation.usable,
            reason_code=evaluation.reason_code if self._settings.mock_mode or not evaluation.usable else AvailabilityReason.DESCRIPTIVE_READY,
            data_mode=DataMode.mock if self._settings.mock_mode else DataMode.real,
            disclaimer='Synthetic demonstration data.' if self._settings.mock_mode else 'Real source inputs; descriptive estimates, inference withheld.',
            simulated=self._settings.mock_mode,
            reason_message=evaluation.message if self._settings.mock_mode or not evaluation.usable else 'Registered data supports descriptive processing only.',
            availability_source='registry_snapshot + mock_demo_gate' if self._settings.mock_mode else 'source_contract_and_native_grid',
            supported_aggregation_policies=list(SUPPORTED_AGGREGATION_POLICIES) if self._settings.mock_mode else [AggregationPolicy.area_weighted],
            warnings=warnings,
        )

    # -- helpers ----------------------------------------------------------
    def _parse_bbox(self, raw: str) -> Aoi:
        parts = [part.strip() for part in raw.split(",")]
        if len(parts) != 4:
            raise InvalidAoiError(
                "bbox must contain four comma-separated values: west,south,east,north",
                received=raw,
            )
        try:
            coordinates = [float(part) for part in parts]
        except ValueError as error:
            raise InvalidAoiError("bbox values must be numbers", received=raw) from error
        try:
            return Aoi(coordinates=coordinates)
        except ValueError as error:
            raise InvalidAoiError(str(error), received=raw) from error

    def _to_summary(self, record: VariableRecord) -> VariableSummary:
        return VariableSummary(
            data_mode=DataMode.mock if self._settings.mock_mode else DataMode.real,
            variable_id=record.variable_id,
            display_name=record.display_name,
            description=record.description,
            unit=record.unit,
            units_verified=record.units_verified,
            unit_source=record.unit_source,
            source=SourceInfo(
                product_id=record.product_id,
                version=record.version,
                source_variable=record.source_variable,
                provider=record.provider,
                documentation_url=record.documentation_url,
                lineage_note=record.lineage_note,
            ),
            availability_state=self._state(record),
            measurement_ready=record.measurement_ready,
            method_ready=record.method_ready,
            app_available=record.app_available,
            demo_available=record.demo_available,
            demo_only=not record.app_available,
        )

    def _to_detail(self, record: VariableRecord) -> VariableDetail:
        summary = self._to_summary(record)
        return VariableDetail(
            **summary.model_dump(),
            aliases=list(record.aliases),
            supported_regions=self._data.supported_region_ids(record.variable_id),
            coverage_start=record.coverage_start,
            coverage_end=record.coverage_end,
            native_grid=record.native_grid,
            limitations=list(record.limitations),
            warnings=[
                "Metadata is a snapshot of the repository registry, not a live NASA query.",
            ]
            + (
                []
                if record.units_verified
                else [f"Unit '{record.unit}' is unverified against repository files."]
            ),
        )

    def _to_region(self, record: RegionRecord) -> RegionSummary:
        return RegionSummary(
            region_id=record.region_id,
            display_name=record.display_name,
            display_name_ar=record.display_name_ar,
            description=record.description,
            bbox=list(record.bbox),
            period_start=record.period_start,
            period_end=record.period_end,
            supported_variable_ids=[v for v in record.supported_variable_ids if record.region_id in self._data.supported_region_ids(v)],
            data_mode=DataMode.mock if self._settings.mock_mode else DataMode.real,
            demo_only=self._settings.mock_mode,
            warnings=[
                "Region bboxes are study windows, not administrative boundaries.",
            ],
        )

    @staticmethod
    def _state(record: VariableRecord) -> CatalogState:
        if record.app_available and record.method_ready:
            return CatalogState.analysis_ready
        if record.measurement_ready:
            return CatalogState.measurement_ready
        return CatalogState.catalogued

    def _known_variable_ids(self) -> list[str]:
        return [record.variable_id for record in self._data.list_variables()]

    def _known_region_ids(self) -> list[str]:
        return [record.region_id for record in self._data.list_regions()]


def ensure_period_within_limits(
    settings: Settings, start_month: str, end_month: str, period_months: int
) -> None:
    """Raise ``InvalidPeriodError`` when the requested span is out of bounds."""
    if period_months < settings.min_period_months:
        raise InvalidPeriodError(
            f"Period must span at least {settings.min_period_months} months.",
            period_months=period_months,
            min_period_months=settings.min_period_months,
        )
    if period_months > settings.max_period_months:
        raise InvalidPeriodError(
            f"Period must not exceed {settings.max_period_months} months.",
            period_months=period_months,
            max_period_months=settings.max_period_months,
        )

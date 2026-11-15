"""Mock statistics adapter.

Produces deterministic synthetic series and descriptive slopes. It never
returns a p-value, confidence interval or significance verdict, because none
was computed - the schema carries ``inference_status='not_computed'`` so a
client cannot mistake the slope for a validated finding.
"""

from __future__ import annotations

from app.adapters.interfaces import ComputedAnalysis, ComputedSpin
from app.core.timeutil import index_to_month, month_to_index
from app.mocks import analyses as synthetic
from app.mocks.analyses import METHOD_ID, METHOD_VERSION
from app.mocks.catalog import VARIABLES_BY_ID
from app.schemas.analysis import AnalysisSpec
from app.schemas.common import ApiWarning, EvidenceState, Severity
from app.schemas.results import DatasetRevision, MethodRef, VariableResult
from app.schemas.spin import SpinRequest, SpinSummary, SpinWindow


class MockStatisticsAdapter:
    """Deterministic stand-in for the statistics team's engine."""

    def compute_analysis(self, spec: AnalysisSpec, *, result_id: str) -> ComputedAnalysis:
        variables: list[VariableResult] = []
        datasets: list[DatasetRevision] = []
        warnings: list[ApiWarning] = [
            ApiWarning(
                code="MOCK_DATA_MODE",
                message="All values are synthetic demonstration data, not NASA observations.",
                severity=Severity.warning,
            ),
            ApiWarning(
                code="METHOD_NOT_APPROVED",
                message=(
                    "The mock method is not scientifically reviewed and must not be cited "
                    "as an approved statistical method."
                ),
                severity=Severity.warning,
            ),
        ]

        for variable_id in spec.variable_ids:
            record = VARIABLES_BY_ID[variable_id]
            series = synthetic.build_series(
                variable_id,
                spec.start_month,
                spec.end_month,
                offset_seed=f"{result_id}:{variable_id}:region",
            )
            trend = synthetic.summarise_trend(variable_id, series)
            variables.append(
                VariableResult(
                    variable_id=variable_id,
                    display_name=record.display_name,
                    unit=record.unit,
                    units_verified=record.units_verified,
                    series=series,
                    trend=trend,
                )
            )
            datasets.append(
                DatasetRevision(
                    variable_id=variable_id,
                    product_id=record.product_id,
                    version=record.version,
                    source_variable=record.source_variable,
                    revision=spec.dataset_revision if len(spec.variable_ids) == 1 else (
                        f"{record.product_id}:{record.version}:{spec.region_id}:mock"
                    ),
                    source="mock_registry_snapshot",
                )
            )
            if not record.units_verified:
                warnings.append(
                    ApiWarning(
                        code="UNIT_UNVERIFIED",
                        message=(
                            f"Unit '{record.unit}' for {variable_id} is taken from product "
                            "documentation and is not asserted by a registry file in this repository."
                        ),
                        severity=Severity.info,
                    )
                )

        return ComputedAnalysis(
            variables=variables,
            method=MethodRef(
                method_id=METHOD_ID,
                method_version=METHOD_VERSION,
                aggregation_policy=spec.aggregation_policy,
            ),
            datasets=datasets,
            warnings=warnings,
        )

    def compute_spin(self, spec: AnalysisSpec, *, result_id: str, request: SpinRequest) -> ComputedSpin:
        """Slide a fixed-length window across the analysis period.

        Windows step one year at a time and never modify the parent result.
        """
        variable_id = spec.variable_ids[0]
        start_index = month_to_index(spec.start_month)
        end_index = month_to_index(spec.end_month)
        coverage_start_year = int(spec.start_month[:4])
        coverage_end_year = int(spec.end_month[:4])

        lower_year = max(coverage_start_year, request.start_year_min or coverage_start_year)
        upper_year = min(coverage_end_year, request.end_year_max or coverage_end_year)
        window_years = max(1, request.minimum_window_years)
        window_months = window_years * 12
        last_start_year = upper_year - window_years

        windows: list[SpinWindow] = []
        for year in range(lower_year, last_start_year + 1):
            window_start_index = max(start_index, year * 12)
            window_end_index = window_start_index + window_months - 1
            if window_end_index > end_index:
                break

            window_start = index_to_month(window_start_index)
            window_end = index_to_month(window_end_index)
            series = synthetic.build_series(
                variable_id,
                window_start,
                window_end,
                offset_seed=f"{result_id}:{variable_id}:spin",
            )
            slope, _, _, _ = synthetic.annual_mean_slope(series)
            rounded = None if slope is None else round(slope, synthetic.SLOPE_DECIMALS)
            windows.append(
                SpinWindow(
                    window_id=f"window_{len(windows) + 1:02d}",
                    start_month=window_start,
                    end_month=window_end,
                    years=round((window_end_index - window_start_index + 1) / 12.0, 2),
                    trend_value=rounded,
                    direction=synthetic.direction_for(rounded, variable_id),
                    evidence_state=EvidenceState.synthetic_demo,
                )
            )
            if len(windows) >= 60:
                break

        values = [window.trend_value for window in windows if window.trend_value is not None]
        positives = sum(1 for value in values if value > 0)
        negatives = sum(1 for value in values if value < 0)
        modal_share = (max(positives, negatives) / len(values)) if values else None

        summary = SpinSummary(
            window_count=len(windows),
            min_trend=None if not values else round(min(values), synthetic.SLOPE_DECIMALS),
            max_trend=None if not values else round(max(values), synthetic.SLOPE_DECIMALS),
            mean_trend=None
            if not values
            else round(sum(values) / len(values), synthetic.SLOPE_DECIMALS),
            sign_agreement_share=None if modal_share is None else round(modal_share, 4),
        )

        warnings = [
            ApiWarning(
                code="SPIN_SYNTHETIC",
                message=(
                    "Spin It windows are computed from synthetic data. Sign agreement is a "
                    "descriptive sensitivity measure, not a probability that the trend is real."
                ),
                severity=Severity.warning,
            )
        ]
        return ComputedSpin(windows=windows, summary=summary, warnings=warnings)

"""Analysis orchestration: validation, cache lookup, job lifecycle, persistence."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone

from app.adapters.interfaces import NASADataAdapter, StatisticsAdapter
from app.core.config import Settings
from app.core.exceptions import (
    DataNotAvailableError,
    InvalidAoiError,
    JobNotFoundError,
    RegionNotFoundError,
    RequestValidationAppError,
    UnsupportedAggregationPolicyError,
    VariableNotFoundError,
)
from app.core.timeutil import month_count
from app.mocks import analyses as synthetic
from app.mocks.spatial import GRID_COLS, GRID_LABEL, GRID_ROWS, build_cell_datasets, missing_cell_count
from app.repositories.interfaces import (
    AnalysisCacheRepository,
    JobRepository,
    ReceiptRepository,
    ResultRepository,
)
from app.repositories.interfaces import CacheEntry
from app.schemas.analysis import (
    AnalysisAcceptedResponse,
    AnalysisRequest,
    AnalysisSpec,
    JobLinks,
    JobState,
    JobStatusResponse,
    StateTransition,
)
from app.schemas.common import ApiWarning, Severity
from app.schemas.results import AnalysisEcho, ResultLinks, ResultResponse, SpatialRef
from app.services.catalog_service import (
    SUPPORTED_AGGREGATION_POLICIES,
    ensure_period_within_limits,
    evaluate_demo_availability,
)
from app.services.receipt_service import build_receipt
from app.workers.mock_job_manager import MockJobManager

logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def short_hash(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:8]


def build_cache_key(
    *,
    variable_ids: list[str],
    region_id: str,
    aoi: list[float],
    start_month: str,
    end_month: str,
    aggregation_policy: str,
    dataset_revision: str,
    method_version: str,
    data_mode: str = "mock",
) -> str:
    """Canonical key. Two requests share a result only when every input matches."""
    parts = [
        "v1",
        data_mode,
        ",".join(sorted(variable_ids)),
        region_id,
        ",".join(f"{coord:.4f}" for coord in aoi),
        start_month,
        end_month,
        aggregation_policy,
        dataset_revision,
        method_version,
    ]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def spec_from_result(result: ResultResponse, data: NASADataAdapter) -> AnalysisSpec:
    """Rebuild the analysis spec of an existing result (used by Spin It)."""
    dataset_revision = ",".join(entry.revision for entry in result.datasets)
    cache_key = build_cache_key(
        variable_ids=result.analysis.variable_ids,
        region_id=result.analysis.region_id,
        aoi=result.analysis.aoi.canonical(),
        start_month=result.analysis.start_month,
        end_month=result.analysis.end_month,
        aggregation_policy=result.analysis.aggregation_policy.value,
        dataset_revision=dataset_revision,
        method_version=result.method.method_version,
    )
    return AnalysisSpec(
        variable_ids=list(result.analysis.variable_ids),
        region_id=result.analysis.region_id,
        aoi=result.analysis.aoi,
        start_month=result.analysis.start_month,
        end_month=result.analysis.end_month,
        aggregation_policy=result.analysis.aggregation_policy,
        period_months=result.analysis.period_months,
        cache_key=cache_key,
        dataset_revision=dataset_revision,
        method_version=result.method.method_version,
    )


class AnalysisService:
    def __init__(
        self,
        *,
        data: NASADataAdapter,
        statistics: StatisticsAdapter,
        jobs: JobRepository,
        results: ResultRepository,
        receipts: ReceiptRepository,
        cache: AnalysisCacheRepository,
        job_manager: MockJobManager,
        settings: Settings,
    ) -> None:
        self._data = data
        self._statistics = statistics
        self._jobs = jobs
        self._results = results
        self._receipts = receipts
        self._cache = cache
        self._job_manager = job_manager
        self._settings = settings

    # -- public API -------------------------------------------------------
    def create_analysis(self, request: AnalysisRequest) -> tuple[AnalysisAcceptedResponse, bool]:
        """Return ``(response, created)``. ``created`` drives 202 vs 200."""
        spec = self._normalise(request)

        cached = self._cache.get(spec.cache_key)
        if cached is not None:
            existing_job = self._jobs.get(cached.job_id)
            if existing_job is not None:
                logger.info("cache hit for key %s", spec.cache_key[:8])
                return self._accepted(existing_job, cached=True), False

        job_id = f"job_mock_{spec.cache_key[:8]}"
        result_id = f"result_mock_{spec.cache_key[:8]}"
        receipt_id = f"receipt_mock_{spec.cache_key[:8]}"
        now = utcnow()

        job = JobStatusResponse(
            job_id=job_id,
            status=JobState.queued,
            result_id=None,
            progress_percent=0,
            request=request,
            resolved_variable_ids=spec.variable_ids,
            warnings=[
                "Mock job. Execution is deterministic and completes without real computation.",
            ],
            state_history=[StateTransition(status=JobState.queued, at=now, message="Job accepted.")],
            created_at=now,
            updated_at=now,
            links=JobLinks(job=f"{self._settings.api_prefix}/analyses/{job_id}"),
        )
        self._jobs.add(job)

        self._job_manager.submit(
            job_id,
            lambda: self._execute(job=job, spec=spec, result_id=result_id, receipt_id=receipt_id),
        )

        stored = self._jobs.get(job_id) or job
        return self._accepted(stored, cached=False), True

    def get_job(self, job_id: str) -> JobStatusResponse:
        job = self._jobs.get(job_id)
        if job is None:
            raise JobNotFoundError(job_id)
        return job

    # -- internals --------------------------------------------------------
    def _normalise(self, request: AnalysisRequest) -> AnalysisSpec:
        resolved_variables: list[str] = []
        known_variables = [record.variable_id for record in self._data.list_variables()]
        for raw_id in request.variable_ids:
            resolved = self._data.resolve_variable_id(raw_id)
            if resolved is None:
                raise VariableNotFoundError(raw_id, known=known_variables)
            if resolved not in resolved_variables:
                resolved_variables.append(resolved)

        if len(resolved_variables) > self._settings.max_variables_per_analysis:
            raise RequestValidationAppError(
                f"At most {self._settings.max_variables_per_analysis} variables may be requested.",
                details={
                    "requested": len(resolved_variables),
                    "max_variables": self._settings.max_variables_per_analysis,
                },
            )

        resolved_region = self._data.resolve_region_id(request.region_id)
        if resolved_region is None:
            raise RegionNotFoundError(
                request.region_id, known=[region.region_id for region in self._data.list_regions()]
            )
        region = self._data.get_region(resolved_region)
        assert region is not None

        aoi = request.aoi
        if aoi is None:
            try:
                from app.schemas.common import Aoi

                aoi = Aoi(type="bbox", coordinates=list(region.bbox))
            except ValueError as error:  # pragma: no cover - registry bbox is valid
                raise InvalidAoiError(str(error)) from error

        self._validate_aoi(aoi)

        period_months = month_count(request.start_month, request.end_month)
        ensure_period_within_limits(
            self._settings, request.start_month, request.end_month, period_months
        )

        if request.aggregation_policy not in SUPPORTED_AGGREGATION_POLICIES:
            raise UnsupportedAggregationPolicyError(
                request.aggregation_policy.value,
                [policy.value for policy in SUPPORTED_AGGREGATION_POLICIES],
            )

        evaluation = evaluate_demo_availability(
            self._data,
            variable_id=resolved_variables[0],
            region_id=resolved_region,
            start_month=request.start_month,
            end_month=request.end_month,
            aoi=aoi,
        )
        if not evaluation.usable:
            raise DataNotAvailableError(evaluation.message, **evaluation.details)

        for variable_id in resolved_variables[1:]:
            other = evaluate_demo_availability(
                self._data,
                variable_id=variable_id,
                region_id=resolved_region,
                start_month=request.start_month,
                end_month=request.end_month,
                aoi=aoi,
            )
            if not other.usable:
                raise DataNotAvailableError(other.message, **other.details)

        dataset_revision = ",".join(
            self._data.dataset_revision(variable_id, resolved_region)
            for variable_id in resolved_variables
        )
        method_version = synthetic.METHOD_VERSION
        cache_key = build_cache_key(
            variable_ids=resolved_variables,
            region_id=resolved_region,
            aoi=aoi.canonical(),
            start_month=request.start_month,
            end_month=request.end_month,
            aggregation_policy=request.aggregation_policy.value,
            dataset_revision=dataset_revision,
            method_version=method_version,
        )

        return AnalysisSpec(
            variable_ids=resolved_variables,
            region_id=resolved_region,
            aoi=aoi,
            start_month=request.start_month,
            end_month=request.end_month,
            aggregation_policy=request.aggregation_policy,
            period_months=period_months,
            cache_key=cache_key,
            dataset_revision=dataset_revision,
            method_version=method_version,
        )

    def _validate_aoi(self, aoi) -> None:
        if aoi.width < self._settings.min_aoi_span_degrees:
            raise InvalidAoiError(
                f"AOI width must be at least {self._settings.min_aoi_span_degrees} degrees.",
                width=round(aoi.width, 4),
            )
        if aoi.height < self._settings.min_aoi_span_degrees:
            raise InvalidAoiError(
                f"AOI height must be at least {self._settings.min_aoi_span_degrees} degrees.",
                height=round(aoi.height, 4),
            )
        if aoi.width > self._settings.max_aoi_span_degrees:
            raise InvalidAoiError(
                f"AOI width must not exceed {self._settings.max_aoi_span_degrees} degrees.",
                width=round(aoi.width, 4),
            )
        if aoi.height > self._settings.max_aoi_span_degrees:
            raise InvalidAoiError(
                f"AOI height must not exceed {self._settings.max_aoi_span_degrees} degrees.",
                height=round(aoi.height, 4),
            )

    def _execute(
        self,
        *,
        job: JobStatusResponse,
        spec: AnalysisSpec,
        result_id: str,
        receipt_id: str,
    ) -> str:
        """Deterministic, synchronous execution of one mock analysis."""
        job.status = JobState.running
        job.progress_percent = 40
        job.updated_at = utcnow()
        job.state_history.append(
            StateTransition(status=JobState.running, at=job.updated_at, message="Mock computation started.")
        )
        self._jobs.replace(job)

        try:
            computed = self._statistics.compute_analysis(spec, result_id=result_id)
            region = self._data.get_region(spec.region_id)
            region_name = region.display_name if region else spec.region_id
            prefix = self._settings.api_prefix

            cells = build_cell_datasets(
                spec.variable_ids[0],
                spec.aoi.canonical(),
                spec.start_month,
                spec.end_month,
                seed_key=result_id,
            )

            warnings = list(computed.warnings)
            warnings.append(
                ApiWarning(
                    code="REGIONAL_AVERAGE_HIDES_VARIATION",
                    message=(
                        "Cells in this demo grid are generated independently; the regional "
                        "series is not an area-weighted aggregate of the cells."
                    ),
                    severity=Severity.info,
                )
            )

            result = ResultResponse(
                result_id=result_id,
                job_id=job.job_id,
                analysis=AnalysisEcho(
                    variable_ids=spec.variable_ids,
                    region_id=spec.region_id,
                    region_display_name=region_name,
                    aoi=spec.aoi,
                    start_month=spec.start_month,
                    end_month=spec.end_month,
                    period_months=spec.period_months,
                    aggregation_policy=spec.aggregation_policy,
                ),
                datasets=computed.datasets,
                method=computed.method,
                variables=computed.variables,
                warnings=warnings,
                spatial=SpatialRef(
                    spatial_url=f"{prefix}/results/{result_id}/spatial",
                    cell_count=GRID_ROWS * GRID_COLS,
                    missing_cell_count=missing_cell_count(cells),
                    grid=GRID_LABEL,
                ),
                receipt_id=receipt_id,
                links=ResultLinks(
                    self_url=f"{prefix}/results/{result_id}",
                    spatial=f"{prefix}/results/{result_id}/spatial",
                    receipt=f"{prefix}/receipts/{receipt_id}",
                    receipt_download=f"{prefix}/receipts/{receipt_id}/download",
                ),
                created_at=utcnow(),
            )

            receipt = build_receipt(
                result,
                receipt_id=receipt_id,
                registry_snapshot=self._data.registry_snapshot(),
                api_prefix=prefix,
            )

            self._results.add(result)
            self._receipts.add(receipt)
            self._cache.put(
                CacheEntry(
                    cache_key=spec.cache_key,
                    job_id=job.job_id,
                    result_id=result_id,
                    receipt_id=receipt_id,
                )
            )

            job.status = JobState.completed
            job.progress_percent = 100
            job.result_id = result_id
            job.links.result = f"{prefix}/results/{result_id}"
            job.updated_at = utcnow()
            job.state_history.append(
                StateTransition(
                    status=JobState.completed,
                    at=job.updated_at,
                    message="Mock result stored.",
                )
            )
            self._jobs.replace(job)
            return result_id

        except Exception as error:  # noqa: BLE001 - job failure must be recorded
            logger.exception("mock analysis failed for job %s", job.job_id)
            job.status = JobState.failed
            job.progress_percent = 100
            job.error = f"{type(error).__name__}: {error}"
            job.updated_at = utcnow()
            job.state_history.append(
                StateTransition(status=JobState.failed, at=job.updated_at, message="Mock computation failed.")
            )
            self._jobs.replace(job)
            raise

    def _accepted(self, job: JobStatusResponse, *, cached: bool) -> AnalysisAcceptedResponse:
        prefix = self._settings.api_prefix
        if cached:
            message = "An equivalent analysis already exists; the cached job was returned."
        elif job.status is JobState.completed:
            message = "Analysis accepted and completed synchronously by the mock job manager."
        else:
            message = "Analysis accepted and queued."
        return AnalysisAcceptedResponse(
            job_id=job.job_id,
            status=job.status,
            result_id=job.result_id,
            cached=cached,
            links=JobLinks(
                job=f"{prefix}/analyses/{job.job_id}",
                result=None if job.result_id is None else f"{prefix}/results/{job.result_id}",
            ),
            message=message,
        )

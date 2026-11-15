"""Composition root and FastAPI dependency providers.

Everything is built once per application instance and stored on
``app.state.container``. Tests therefore get a fully isolated set of in-memory
repositories simply by creating a new app.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from app.adapters.interfaces import NASADataAdapter, RAGAdapter, StatisticsAdapter
from app.adapters.mock_nasa_data import MockNASADataAdapter
from app.adapters.mock_rag import MockRAGAdapter
from app.adapters.mock_statistics import MockStatisticsAdapter
from app.core.config import Settings, get_settings
from app.repositories.interfaces import (
    AnalysisCacheRepository,
    JobRepository,
    ReceiptRepository,
    ResultRepository,
    SpinRepository,
)
from app.repositories.memory import (
    InMemoryAnalysisCacheRepository,
    InMemoryJobRepository,
    InMemoryReceiptRepository,
    InMemoryResultRepository,
    InMemorySpinRepository,
)
from app.services.analysis_service import AnalysisService
from app.services.catalog_service import CatalogService
from app.services.comparison_service import ComparisonService
from app.services.explanation_service import ExplanationService
from app.services.receipt_service import ReceiptService
from app.services.recommendation_service import RecommendationService
from app.services.result_service import ResultService
from app.services.spatial_service import SpatialService
from app.services.spin_service import SpinService
from app.workers.mock_job_manager import MockJobManager


@dataclass
class Container:
    settings: Settings

    # adapters
    data: NASADataAdapter
    statistics: StatisticsAdapter
    rag: RAGAdapter

    # repositories
    jobs_repo: JobRepository
    results_repo: ResultRepository
    receipts_repo: ReceiptRepository
    spins_repo: SpinRepository
    cache: AnalysisCacheRepository
    job_manager: MockJobManager

    # services
    catalog: CatalogService
    analysis: AnalysisService
    result: ResultService
    spatial: SpatialService
    comparison: ComparisonService
    spin: SpinService
    recommendation: RecommendationService
    explanation: ExplanationService
    receipt: ReceiptService


def build_container(settings: Settings | None = None) -> Container:
    settings = settings or get_settings()

    data = MockNASADataAdapter()
    statistics = MockStatisticsAdapter()
    rag = MockRAGAdapter()

    jobs_repo = InMemoryJobRepository()
    results_repo = InMemoryResultRepository()
    receipts_repo = InMemoryReceiptRepository()
    spins_repo = InMemorySpinRepository()
    cache = InMemoryAnalysisCacheRepository()
    job_manager = MockJobManager(auto_complete=settings.mock_auto_complete_jobs)

    result_service = ResultService(results_repo)

    return Container(
        settings=settings,
        data=data,
        statistics=statistics,
        rag=rag,
        jobs_repo=jobs_repo,
        results_repo=results_repo,
        receipts_repo=receipts_repo,
        spins_repo=spins_repo,
        cache=cache,
        job_manager=job_manager,
        catalog=CatalogService(data, settings),
        analysis=AnalysisService(
            data=data,
            statistics=statistics,
            jobs=jobs_repo,
            results=results_repo,
            receipts=receipts_repo,
            cache=cache,
            job_manager=job_manager,
            settings=settings,
        ),
        result=result_service,
        spatial=SpatialService(result_service, settings),
        comparison=ComparisonService(result_service, settings),
        spin=SpinService(
            results=result_service,
            spins=spins_repo,
            statistics=statistics,
            data=data,
            settings=settings,
        ),
        recommendation=RecommendationService(data, rag, settings),
        explanation=ExplanationService(results=result_service, jobs=jobs_repo, rag=rag),
        receipt=ReceiptService(receipts_repo),
    )


def get_container(request: Request) -> Container:
    """FastAPI dependency returning the container bound to this app instance."""
    return request.app.state.container

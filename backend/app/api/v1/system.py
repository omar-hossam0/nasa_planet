"""System endpoints: liveness and readiness."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.dependencies import Container, get_container
from app.schemas.system import (
    HealthResponse,
    IntegrationState,
    IntegrationStatus,
    ReadinessResponse,
    ServiceStatus,
)

router = APIRouter(tags=["system"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness probe",
    description="Confirms the API process is up. Does not check any external dependency.",
)
def health(container: Container = Depends(get_container)) -> HealthResponse:
    settings = container.settings
    return HealthResponse(
        status=ServiceStatus.ok,
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        mock_mode=settings.mock_mode,
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness with honest dependency state",
    description=(
        "Separates 'the API answers' from 'real science is wired up'. In this milestone every "
        "external integration is reported as mock or not_integrated - never as connected."
    ),
)
def ready(container: Container = Depends(get_container)) -> ReadinessResponse:
    settings = container.settings
    integrations = [
        IntegrationStatus(
            name="database",
            state=IntegrationState.not_integrated,
            detail="No database is provisioned. Repositories are in-process dictionaries.",
        ),
        IntegrationStatus(
            name="statistics_engine",
            state=IntegrationState.mock,
            detail="MockStatisticsAdapter returns deterministic synthetic series and descriptive slopes.",
        ),
        IntegrationStatus(
            name="rag_service",
            state=IntegrationState.mock,
            detail="MockRAGAdapter uses keyword rules and templates. No model, no retrieval.",
        ),
        IntegrationStatus(
            name="nasa_data",
            state=IntegrationState.mock,
            detail="Catalog is served from a repository snapshot. No NetCDF file is read at request time.",
        ),
        IntegrationStatus(
            name="job_queue",
            state=IntegrationState.mock,
            detail="In-process mock job manager. Not durable and not shared between workers.",
        ),
        IntegrationStatus(
            name="frontend",
            state=IntegrationState.not_integrated,
            detail="No frontend is integrated. CORS is pre-configured for local development origins.",
        ),
    ]

    return ReadinessResponse(
        status=ServiceStatus.ok if settings.mock_mode else ServiceStatus.degraded,
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        mock_mode=settings.mock_mode,
        api_running=True,
        mock_services_available=settings.mock_mode,
        integrations=integrations,
        notes=[
            "Ready to serve mock-backed requests." if settings.mock_mode else
            "MOCK_MODE is disabled but no real integration exists; endpoints will report 503.",
            "All numeric payloads are synthetic demonstration data.",
        ],
    )

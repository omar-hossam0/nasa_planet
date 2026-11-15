"""System-level schemas: liveness and readiness."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ServiceStatus(str, Enum):
    ok = "ok"
    degraded = "degraded"


class IntegrationState(str, Enum):
    """Honest state of an external dependency."""

    mock = "mock"
    not_integrated = "not_integrated"
    connected = "connected"
    unavailable = "unavailable"


class IntegrationStatus(BaseModel):
    name: str
    state: IntegrationState
    detail: str


class HealthResponse(BaseModel):
    status: ServiceStatus = ServiceStatus.ok
    app_name: str
    version: str
    environment: str
    mock_mode: bool
    message: str = "Service is running."


class ReadinessResponse(BaseModel):
    """Readiness separates "the API answers" from "real science is wired up"."""

    status: ServiceStatus
    app_name: str
    version: str
    environment: str
    mock_mode: bool
    api_running: bool = True
    mock_services_available: bool
    integrations: list[IntegrationStatus] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

"""Shared pytest fixtures.

Every test gets a brand-new application instance, therefore brand-new in-memory
repositories. No database, network or external service is involved.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app

BASE_ANALYSIS: dict = {
    "variable_ids": ["air_temperature"],
    "region_id": "nile_corridor",
    "aoi": {"type": "bbox", "coordinates": [29.0, 24.0, 33.0, 32.0]},
    "start_month": "2005-01",
    "end_month": "2020-12",
    "aggregation_policy": "area_weighted",
}


def make_settings(**overrides) -> Settings:
    defaults = dict(
        app_name="Trend Detective Backend",
        app_env="test",
        mock_mode=True,
        mock_auto_complete_jobs=True,
        log_level="WARNING",
        api_prefix="/v1",
    )
    defaults.update(overrides)
    return Settings(**defaults)


@pytest.fixture()
def settings() -> Settings:
    return make_settings()


@pytest.fixture()
def app(settings: Settings):
    return create_app(settings)


@pytest.fixture()
def client(app) -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def container(app):
    return app.state.container


@pytest.fixture()
def analysis_payload() -> dict:
    """Fresh copy so a test mutating it cannot leak into another test."""
    return {
        **BASE_ANALYSIS,
        "variable_ids": list(BASE_ANALYSIS["variable_ids"]),
        "aoi": {
            "type": "bbox",
            "coordinates": list(BASE_ANALYSIS["aoi"]["coordinates"]),
        },
    }


@pytest.fixture()
def created_analysis(client: TestClient, analysis_payload: dict) -> dict:
    response = client.post("/v1/analyses", json=analysis_payload)
    assert response.status_code == 202, response.text
    return response.json()


@pytest.fixture()
def result_id(created_analysis: dict) -> str:
    value = created_analysis.get("result_id")
    assert value, "mock job should complete inline"
    return value


@pytest.fixture()
def result(client: TestClient, result_id: str) -> dict:
    response = client.get(f"/v1/results/{result_id}")
    assert response.status_code == 200, response.text
    return response.json()

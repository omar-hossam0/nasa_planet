"""Tests for GET /health, GET /ready and the OpenAPI surface."""

from __future__ import annotations

from fastapi.testclient import TestClient

EXPECTED_PATHS = {
    "/health",
    "/ready",
    "/v1/catalog",
    "/v1/catalog/variables/{variable_id}",
    "/v1/catalog/regions",
    "/v1/catalog/availability",
    "/v1/recommendations",
    "/v1/analyses",
    "/v1/analyses/{job_id}",
    "/v1/results/{result_id}",
    "/v1/results/{result_id}/spatial",
    "/v1/results/{result_id}/cells/{cell_id}",
    "/v1/comparisons",
    "/v1/results/{result_id}/spin",
    "/v1/spin/{spin_id}",
    "/v1/explanations",
    "/v1/receipts/{receipt_id}",
    "/v1/receipts/{receipt_id}/download",
}


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["app_name"] == "Trend Detective Backend"
    assert body["environment"] == "test"
    assert body["mock_mode"] is True


def test_health_echoes_request_id(client: TestClient) -> None:
    response = client.get("/health", headers={"X-Request-ID": "req_custom123"})
    assert response.headers["X-Request-ID"] == "req_custom123"


def test_health_generates_request_id_when_absent(client: TestClient) -> None:
    response = client.get("/health")
    assert response.headers["X-Request-ID"].startswith("req_")


def test_ready_reports_mock_state_honestly(client: TestClient) -> None:
    response = client.get("/ready")
    assert response.status_code == 200
    body = response.json()

    assert body["api_running"] is True
    assert body["mock_services_available"] is True

    states = {item["name"]: item["state"] for item in body["integrations"]}
    assert states["database"] == "not_integrated"
    assert states["statistics_engine"] == "mock"
    assert states["rag_service"] == "mock"
    assert states["nasa_data"] == "mock"
    assert states["frontend"] == "not_integrated"
    # Nothing may be reported as connected while no real integration exists.
    assert "connected" not in states.values()


def test_openapi_lists_all_eighteen_routes(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    assert set(spec["paths"]) == EXPECTED_PATHS
    assert len(spec["paths"]) == 18


def test_docs_page_loads(client: TestClient) -> None:
    response = client.get("/docs")
    assert response.status_code == 200
    assert "swagger" in response.text.lower()


def test_error_envelope_shape_for_unknown_route(client: TestClient) -> None:
    response = client.get("/v1/does-not-exist")
    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "NOT_FOUND"
    assert error["request_id"].startswith("req_")
    assert set(error) == {"code", "message", "details", "request_id"}

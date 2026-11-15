"""Tests for analysis creation and job polling."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import make_settings


def test_create_analysis_returns_202_and_completes(client: TestClient, analysis_payload: dict) -> None:
    response = client.post("/v1/analyses", json=analysis_payload)
    assert response.status_code == 202

    body = response.json()
    assert body["status"] == "completed"
    assert body["cached"] is False
    assert body["data_mode"] == "mock"
    assert body["job_id"].startswith("job_mock_")
    assert body["result_id"].startswith("result_mock_")
    assert body["links"]["job"] == f"/v1/analyses/{body['job_id']}"


def test_equivalent_request_reuses_cached_result(client: TestClient, analysis_payload: dict) -> None:
    first = client.post("/v1/analyses", json=analysis_payload)
    second = client.post("/v1/analyses", json=analysis_payload)

    assert first.status_code == 202
    assert second.status_code == 200
    assert second.json()["cached"] is True
    assert second.json()["job_id"] == first.json()["job_id"]
    assert second.json()["result_id"] == first.json()["result_id"]


def test_different_period_produces_different_result(client: TestClient, analysis_payload: dict) -> None:
    first = client.post("/v1/analyses", json=analysis_payload).json()

    other = {**analysis_payload, "end_month": "2019-12"}
    second = client.post("/v1/analyses", json=other).json()

    assert second["cached"] is False
    assert second["job_id"] != first["job_id"]


def test_job_poll_returns_completed_with_result(client: TestClient, created_analysis: dict) -> None:
    job_id = created_analysis["job_id"]
    response = client.get(f"/v1/analyses/{job_id}")
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "completed"
    assert body["result_id"] == created_analysis["result_id"]
    assert body["progress_percent"] == 100
    assert [entry["status"] for entry in body["state_history"]] == [
        "queued",
        "running",
        "completed",
    ]
    assert body["resolved_variable_ids"] == ["air_temperature"]


def test_unknown_job_returns_404(client: TestClient) -> None:
    response = client.get("/v1/analyses/job_mock_missing")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "JOB_NOT_FOUND"


def test_start_after_end_is_rejected(client: TestClient, analysis_payload: dict) -> None:
    payload = {**analysis_payload, "start_month": "2020-01", "end_month": "2005-12"}
    response = client.post("/v1/analyses", json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_invalid_month_format_is_rejected(client: TestClient, analysis_payload: dict) -> None:
    payload = {**analysis_payload, "start_month": "2005-1"}
    response = client.post("/v1/analyses", json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_period_shorter_than_minimum_is_rejected(client: TestClient, analysis_payload: dict) -> None:
    payload = {**analysis_payload, "start_month": "2005-01", "end_month": "2005-06"}
    response = client.post("/v1/analyses", json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_PERIOD"


def test_inverted_bbox_is_rejected(client: TestClient, analysis_payload: dict) -> None:
    payload = {**analysis_payload, "aoi": {"type": "bbox", "coordinates": [33.0, 31.0, 29.0, 24.0]}}
    response = client.post("/v1/analyses", json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_oversized_bbox_is_rejected(client: TestClient, analysis_payload: dict) -> None:
    payload = {**analysis_payload, "aoi": {"type": "bbox", "coordinates": [-20.0, 0.0, 25.0, 35.0]}}
    response = client.post("/v1/analyses", json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_AOI"


def test_bbox_outside_region_is_unavailable(client: TestClient, analysis_payload: dict) -> None:
    payload = {**analysis_payload, "aoi": {"type": "bbox", "coordinates": [0.0, 0.0, 5.0, 5.0]}}
    response = client.post("/v1/analyses", json=payload)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DATA_NOT_AVAILABLE"


def test_period_outside_coverage_is_unavailable(client: TestClient, analysis_payload: dict) -> None:
    payload = {**analysis_payload, "start_month": "1990-01", "end_month": "1995-12"}
    response = client.post("/v1/analyses", json=payload)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DATA_NOT_AVAILABLE"


def test_unknown_variable_returns_404(client: TestClient, analysis_payload: dict) -> None:
    payload = {**analysis_payload, "variable_ids": ["co2"]}
    response = client.post("/v1/analyses", json=payload)
    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "VARIABLE_NOT_FOUND"
    assert error["details"]["variable_id"] == "co2"


def test_unknown_region_returns_404(client: TestClient, analysis_payload: dict) -> None:
    payload = {**analysis_payload, "region_id": "atlantis"}
    response = client.post("/v1/analyses", json=payload)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "REGION_NOT_FOUND"


def test_unsupported_aggregation_policy_is_rejected(client: TestClient, analysis_payload: dict) -> None:
    payload = {**analysis_payload, "aggregation_policy": "unweighted_mean"}
    response = client.post("/v1/analyses", json=payload)
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "UNSUPPORTED_AGGREGATION_POLICY"
    assert "area_weighted" in error["details"]["supported_policies"]


def test_missing_required_field_is_rejected(client: TestClient) -> None:
    response = client.post("/v1/analyses", json={"variable_ids": ["air_temperature"]})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    locations = {item["loc"] for item in error["details"]["errors"]}
    assert any("region_id" in location for location in locations)


def test_extra_field_is_rejected(client: TestClient, analysis_payload: dict) -> None:
    payload = {**analysis_payload, "unexpected": True}
    response = client.post("/v1/analyses", json=payload)
    assert response.status_code == 422


def test_legacy_region_alias_is_resolved(client: TestClient, analysis_payload: dict) -> None:
    payload = {**analysis_payload, "region_id": "egypt"}
    response = client.post("/v1/analyses", json=payload)
    assert response.status_code == 202
    job = client.get(f"/v1/analyses/{response.json()['job_id']}").json()
    assert job["resolved_variable_ids"] == ["air_temperature"]
    result = client.get(f"/v1/results/{response.json()['result_id']}").json()
    assert result["analysis"]["region_id"] == "nile_corridor"


def test_queued_job_can_be_advanced_manually() -> None:
    """With auto-completion disabled the full lifecycle is observable."""
    from app.main import create_app

    app = create_app(make_settings(mock_auto_complete_jobs=False))
    with TestClient(app) as client:
        payload = {
            "variable_ids": ["soil_moisture"],
            "region_id": "nile_corridor",
            "start_month": "2005-01",
            "end_month": "2020-12",
        }
        created = client.post("/v1/analyses", json=payload)
        assert created.status_code == 202
        job_id = created.json()["job_id"]
        assert created.json()["status"] == "queued"
        assert created.json()["result_id"] is None

        polled = client.get(f"/v1/analyses/{job_id}").json()
        assert polled["status"] == "queued"

        executed = app.state.container.job_manager.run_pending()
        assert executed == [job_id]

        finished = client.get(f"/v1/analyses/{job_id}").json()
        assert finished["status"] == "completed"
        assert finished["result_id"]

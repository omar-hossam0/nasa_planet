"""Tests for the Spin It endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

SPIN_BODY = {"minimum_window_years": 10, "start_year_min": 2001, "end_year_max": 2024}


def _full_period_result(client: TestClient) -> str:
    payload = {
        "variable_ids": ["air_temperature"],
        "region_id": "nile_corridor",
        "start_month": "2001-01",
        "end_month": "2024-12",
    }
    created = client.post("/v1/analyses", json=payload)
    assert created.status_code == 202, created.text
    return created.json()["result_id"]


def test_create_spin(client: TestClient) -> None:
    result_id = _full_period_result(client)
    response = client.post(f"/v1/results/{result_id}/spin", json=SPIN_BODY)
    assert response.status_code == 202

    body = response.json()
    assert body["status"] == "completed"
    assert body["result_id"] == result_id
    assert body["spin_id"].startswith("spin_mock_")
    assert body["data_mode"] == "mock"
    assert body["links"]["self_url"] == f"/v1/spin/{body['spin_id']}"


def test_spin_windows_are_returned(client: TestClient) -> None:
    result_id = _full_period_result(client)
    spin_id = client.post(f"/v1/results/{result_id}/spin", json=SPIN_BODY).json()["spin_id"]

    response = client.get(f"/v1/spin/{spin_id}")
    assert response.status_code == 200
    body = response.json()

    assert body["result_id"] == result_id
    assert body["status"] == "completed"
    assert body["variable_id"] == "air_temperature"
    assert body["trend_unit"] == "K year-1"
    assert body["data_mode"] == "mock"

    windows = body["windows"]
    assert len(windows) == 14
    assert windows[0]["start_month"] == "2001-01"
    assert windows[0]["end_month"] == "2010-12"
    assert windows[0]["years"] == 10.0
    assert windows[-1]["start_month"] == "2014-01"
    for window in windows:
        assert window["window_id"].startswith("window_")
        assert window["evidence_state"] == "synthetic_demo"
        assert window["direction"] in {"increasing", "decreasing", "inconclusive"}


def test_spin_summary_is_descriptive(client: TestClient) -> None:
    result_id = _full_period_result(client)
    spin_id = client.post(f"/v1/results/{result_id}/spin", json=SPIN_BODY).json()["spin_id"]
    summary = client.get(f"/v1/spin/{spin_id}").json()["summary"]

    assert summary["window_count"] == 14
    assert summary["min_trend"] <= summary["mean_trend"] <= summary["max_trend"]
    assert 0.0 <= summary["sign_agreement_share"] <= 1.0
    assert "not a statistical test" in summary["note"].lower()


def test_spin_does_not_modify_parent_result(client: TestClient) -> None:
    result_id = _full_period_result(client)
    before = client.get(f"/v1/results/{result_id}").json()

    client.post(f"/v1/results/{result_id}/spin", json=SPIN_BODY)

    after = client.get(f"/v1/results/{result_id}").json()
    assert before == after


def test_spin_is_deterministic(client: TestClient) -> None:
    result_id = _full_period_result(client)
    first = client.post(f"/v1/results/{result_id}/spin", json=SPIN_BODY).json()
    second = client.post(f"/v1/results/{result_id}/spin", json=SPIN_BODY).json()
    assert first["spin_id"] == second["spin_id"]

    body_first = client.get(f"/v1/spin/{first['spin_id']}").json()
    body_second = client.get(f"/v1/spin/{second['spin_id']}").json()
    assert body_first["windows"] == body_second["windows"]


def test_window_longer_than_period_is_rejected(client: TestClient, result_id: str) -> None:
    response = client.post(
        f"/v1/results/{result_id}/spin",
        json={"minimum_window_years": 30},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_SPIN_WINDOW"


def test_years_outside_coverage_are_rejected(client: TestClient, result_id: str) -> None:
    response = client.post(
        f"/v1/results/{result_id}/spin",
        json={"minimum_window_years": 5, "start_year_min": 1990},
    )
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "INVALID_SPIN_WINDOW"
    assert error["details"]["coverage"] == [2005, 2020]


def test_end_year_after_coverage_is_rejected(client: TestClient, result_id: str) -> None:
    response = client.post(
        f"/v1/results/{result_id}/spin",
        json={"minimum_window_years": 5, "end_year_max": 2035},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_SPIN_WINDOW"


def test_zero_window_years_is_rejected_by_schema(client: TestClient, result_id: str) -> None:
    response = client.post(f"/v1/results/{result_id}/spin", json={"minimum_window_years": 0})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_unknown_result_returns_404(client: TestClient) -> None:
    response = client.post("/v1/results/result_mock_missing/spin", json=SPIN_BODY)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESULT_NOT_FOUND"


def test_unknown_spin_returns_404(client: TestClient) -> None:
    response = client.get("/v1/spin/spin_mock_missing")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SPIN_NOT_FOUND"

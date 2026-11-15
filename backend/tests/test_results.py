"""Tests for GET /v1/results/{result_id}."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_result_structure_and_mock_markers(client: TestClient, result: dict) -> None:
    assert result["data_mode"] == "mock"
    assert "Synthetic" in result["disclaimer"]
    assert result["evidence_state"] == "synthetic_demo"
    assert result["result_id"].startswith("result_mock_")
    assert result["receipt_id"].startswith("receipt_mock_")


def test_result_echoes_the_request(client: TestClient, result: dict) -> None:
    analysis = result["analysis"]
    assert analysis["variable_ids"] == ["air_temperature"]
    assert analysis["region_id"] == "nile_corridor"
    assert analysis["region_display_name"] == "Nile corridor (Egypt rectangle)"
    assert analysis["start_month"] == "2005-01"
    assert analysis["end_month"] == "2020-12"
    assert analysis["period_months"] == 192
    assert analysis["aoi"]["coordinates"] == [29.0, 24.0, 33.0, 32.0]


def test_result_series_is_complete_monthly(client: TestClient, result: dict) -> None:
    series = result["variables"][0]["series"]
    assert len(series) == 192
    assert series[0]["month"] == "2005-01"
    assert series[-1]["month"] == "2020-12"
    assert all(point["missing"] is False for point in series)
    assert all(point["value"] is not None for point in series)


def test_trend_is_descriptive_not_inferential(client: TestClient, result: dict) -> None:
    trend = result["variables"][0]["trend"]
    assert trend["method_id"] == "mock_seasonal_linear_v0"
    assert trend["inference_status"] == "not_computed"
    assert trend["p_value"] is None
    assert trend["evidence_state"] == "synthetic_demo"
    assert trend["direction"] in {"increasing", "decreasing", "inconclusive"}
    assert trend["slope_unit"] == "K year-1"
    assert trend["notes"]


def test_units_and_datasets_are_reported(client: TestClient, result: dict) -> None:
    variable = result["variables"][0]
    assert variable["unit"] == "K"
    assert variable["units_verified"] is True

    dataset = result["datasets"][0]
    assert dataset["product_id"] == "M2TMNXSLV"
    assert dataset["version"] == "5.12.4"
    assert dataset["source"] == "mock_registry_snapshot"
    assert dataset["revision"].endswith(":mock")


def test_method_is_marked_unapproved(client: TestClient, result: dict) -> None:
    method = result["method"]
    assert method["approved"] is False
    assert method["status"] == "mock_synthetic"
    assert "not been scientifically reviewed" in method["note"]


def test_result_carries_warnings(client: TestClient, result: dict) -> None:
    codes = {warning["code"] for warning in result["warnings"]}
    assert "MOCK_DATA_MODE" in codes
    assert "METHOD_NOT_APPROVED" in codes


def test_spatial_and_receipt_links_are_present(client: TestClient, result: dict) -> None:
    assert result["spatial"]["cell_count"] == 9
    assert result["spatial"]["missing_cell_count"] == 1
    assert result["links"]["spatial"] == f"/v1/results/{result['result_id']}/spatial"
    assert result["links"]["receipt"] == f"/v1/receipts/{result['receipt_id']}"


def test_multi_variable_result(client: TestClient, analysis_payload: dict) -> None:
    payload = {
        **analysis_payload,
        "variable_ids": ["air_temperature", "soil_moisture"],
    }
    created = client.post("/v1/analyses", json=payload).json()
    result = client.get(f"/v1/results/{created['result_id']}").json()

    assert [item["variable_id"] for item in result["variables"]] == [
        "air_temperature",
        "soil_moisture",
    ]
    assert len(result["datasets"]) == 2
    units = {item["variable_id"]: item["unit"] for item in result["variables"]}
    assert units == {"air_temperature": "K", "soil_moisture": "kg m-2"}


def test_unknown_result_returns_404(client: TestClient) -> None:
    response = client.get("/v1/results/result_mock_missing")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESULT_NOT_FOUND"

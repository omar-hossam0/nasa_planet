"""Tests for the spatial grid and cell detail endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_spatial_grid_shape(client: TestClient, result_id: str) -> None:
    response = client.get(f"/v1/results/{result_id}/spatial")
    assert response.status_code == 200
    body = response.json()

    assert body["cell_count"] == 9
    assert body["missing_cell_count"] == 1
    assert body["grid"] == "3x3_regular_lonlat"
    assert body["bounds"] == [29.0, 24.0, 33.0, 32.0]
    assert body["data_mode"] == "mock"
    assert len(body["cells"]) == 9


def test_every_cell_carries_required_fields(client: TestClient, result_id: str) -> None:
    cells = client.get(f"/v1/results/{result_id}/spatial").json()["cells"]
    for cell in cells:
        assert cell["result_id"] == result_id
        assert cell["variable_id"] == "air_temperature"
        assert len(cell["bbox"]) == 4
        assert len(cell["centroid"]) == 2
        assert cell["geometry"]["type"] == "Polygon"
        assert cell["trend_unit"] == "K year-1"
        assert cell["data_mode"] == "mock"
        ring = cell["geometry"]["coordinates"][0]
        assert ring[0] == ring[-1], "polygon ring must be closed"
        assert len(ring) == 5


def test_cell_ids_are_stable_and_ordered(client: TestClient, result_id: str) -> None:
    cells = client.get(f"/v1/results/{result_id}/spatial").json()["cells"]
    assert [cell["cell_id"] for cell in cells] == [f"cell_{index:02d}" for index in range(1, 10)]


def test_missing_cell_is_flagged_not_zero(client: TestClient, result_id: str) -> None:
    cells = {cell["cell_id"]: cell for cell in client.get(f"/v1/results/{result_id}/spatial").json()["cells"]}
    missing = cells["cell_09"]
    assert missing["missing_data"] is True
    assert missing["trend_value"] is None
    assert missing["evidence_state"] == "insufficient_data"
    assert missing["direction"] == "insufficient_data"


def test_cell_detail_matches_spatial_trend(client: TestClient, result_id: str) -> None:
    spatial = client.get(f"/v1/results/{result_id}/spatial").json()
    listed = next(cell for cell in spatial["cells"] if cell["cell_id"] == "cell_01")

    response = client.get(f"/v1/results/{result_id}/cells/cell_01")
    assert response.status_code == 200
    detail = response.json()

    assert detail["cell_id"] == "cell_01"
    assert detail["result_id"] == result_id
    assert detail["bbox"] == listed["bbox"]
    assert detail["centroid"] == listed["centroid"]
    assert detail["trend"]["slope_per_year"] == listed["trend_value"]
    assert len(detail["series"]) == 192
    assert detail["missing_data"] is False


def test_missing_cell_detail_has_no_estimable_trend(client: TestClient, result_id: str) -> None:
    detail = client.get(f"/v1/results/{result_id}/cells/cell_09").json()
    assert detail["missing_data"] is True
    assert detail["trend"]["direction"] == "insufficient_data"
    assert detail["trend"]["slope_per_year"] is None
    assert detail["trend"]["n_months"] == 0
    assert all(point["missing"] for point in detail["series"])
    codes = {warning["code"] for warning in detail["warnings"]}
    assert "CELL_MISSING_DATA" in codes


def test_unknown_cell_returns_404(client: TestClient, result_id: str) -> None:
    response = client.get(f"/v1/results/{result_id}/cells/cell_42")
    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "CELL_NOT_FOUND"
    assert error["details"]["cell_id"] == "cell_42"
    assert error["details"]["result_id"] == result_id


def test_unknown_result_returns_404_for_spatial(client: TestClient) -> None:
    response = client.get("/v1/results/result_mock_missing/spatial")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESULT_NOT_FOUND"


def test_cells_differ_from_the_regional_average(client: TestClient, result_id: str) -> None:
    result = client.get(f"/v1/results/{result_id}").json()
    regional = result["variables"][0]["trend"]["slope_per_year"]
    cells = client.get(f"/v1/results/{result_id}/spatial").json()["cells"]
    values = [cell["trend_value"] for cell in cells if cell["trend_value"] is not None]
    assert any(value != regional for value in values), "cells must not all equal the regional slope"

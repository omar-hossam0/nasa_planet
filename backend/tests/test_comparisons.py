"""Tests for POST /v1/comparisons."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _compare(client: TestClient, result_id: str, cell_ids: list[str]) -> dict:
    return client.post(
        "/v1/comparisons",
        json={"comparison_type": "cells", "result_id": result_id, "cell_ids": cell_ids},
    ).json()


def test_two_cell_comparison(client: TestClient, result_id: str) -> None:
    response = client.post(
        "/v1/comparisons",
        json={"comparison_type": "cells", "result_id": result_id, "cell_ids": ["cell_01", "cell_02"]},
    )
    assert response.status_code == 200
    body = response.json()

    assert body["comparison_type"] == "cells"
    assert body["result_id"] == result_id
    assert body["variable_id"] == "air_temperature"
    assert body["trend_unit"] == "K year-1"
    assert len(body["cells"]) == 2
    assert body["data_mode"] == "mock"
    assert body["chart_hint"] == "multi_line"


def test_comparison_reports_compatibility(client: TestClient, result_id: str) -> None:
    body = _compare(client, result_id, ["cell_01", "cell_02"])
    compatibility = body["compatibility"]
    assert compatibility["compatible"] is True
    for key in (
        "variable_match",
        "unit_match",
        "period_match",
        "method_version_match",
        "dataset_revision_match",
    ):
        assert compatibility[key] is True


def test_comparison_series_is_aligned_per_month(client: TestClient, result_id: str) -> None:
    body = _compare(client, result_id, ["cell_01", "cell_02"])
    series = body["series"]
    assert len(series) == 192
    assert series[0]["month"] == "2005-01"
    assert set(series[0]["values"]) == {"cell_01", "cell_02"}


def test_comparison_deltas_are_relative_to_first_cell(client: TestClient, result_id: str) -> None:
    body = _compare(client, result_id, ["cell_01", "cell_02"])
    deltas = {item["cell_id"]: item for item in body["deltas"]}
    assert deltas["cell_01"]["difference_from_first"] == 0.0

    first = body["cells"][0]["trend_value"]
    second = body["cells"][1]["trend_value"]
    assert deltas["cell_02"]["difference_from_first"] == round(second - first, 6)


def test_comparison_of_three_cells(client: TestClient, result_id: str) -> None:
    body = _compare(client, result_id, ["cell_01", "cell_02", "cell_03"])
    assert len(body["cells"]) == 3
    assert len(body["series"][0]["values"]) == 3


def test_missing_cell_cannot_be_compared(client: TestClient, result_id: str) -> None:
    response = client.post(
        "/v1/comparisons",
        json={"comparison_type": "cells", "result_id": result_id, "cell_ids": ["cell_01", "cell_09"]},
    )
    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "INCOMPATIBLE_COMPARISON"
    assert error["details"]["cell_id"] == "cell_09"


def test_unknown_cell_returns_404(client: TestClient, result_id: str) -> None:
    response = client.post(
        "/v1/comparisons",
        json={"comparison_type": "cells", "result_id": result_id, "cell_ids": ["cell_01", "cell_77"]},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "CELL_NOT_FOUND"


def test_unknown_result_returns_404(client: TestClient) -> None:
    response = client.post(
        "/v1/comparisons",
        json={"comparison_type": "cells", "result_id": "result_mock_missing", "cell_ids": ["cell_01", "cell_02"]},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESULT_NOT_FOUND"


def test_single_cell_is_rejected(client: TestClient, result_id: str) -> None:
    response = client.post(
        "/v1/comparisons",
        json={"comparison_type": "cells", "result_id": result_id, "cell_ids": ["cell_01"]},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_five_cells_are_rejected(client: TestClient, result_id: str) -> None:
    response = client.post(
        "/v1/comparisons",
        json={
            "comparison_type": "cells",
            "result_id": result_id,
            "cell_ids": ["cell_01", "cell_02", "cell_03", "cell_04", "cell_05"],
        },
    )
    assert response.status_code == 422


def test_duplicate_cells_are_rejected(client: TestClient, result_id: str) -> None:
    response = client.post(
        "/v1/comparisons",
        json={"comparison_type": "cells", "result_id": result_id, "cell_ids": ["cell_01", "cell_01"]},
    )
    assert response.status_code == 422


def test_unsupported_comparison_type_is_rejected(client: TestClient, result_id: str) -> None:
    response = client.post(
        "/v1/comparisons",
        json={"comparison_type": "regions", "result_id": result_id, "cell_ids": ["cell_01", "cell_02"]},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"

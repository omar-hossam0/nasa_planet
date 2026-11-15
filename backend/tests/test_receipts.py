"""Tests for the evidence receipt endpoints."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient


def test_receipt_links_to_result(client: TestClient, result: dict) -> None:
    receipt_id = result["receipt_id"]
    response = client.get(f"/v1/receipts/{receipt_id}")
    assert response.status_code == 200

    body = response.json()
    assert body["receipt_id"] == receipt_id
    assert body["result_id"] == result["result_id"]
    assert body["job_id"] == result["job_id"]
    assert body["variable_ids"] == ["air_temperature"]
    assert body["region_id"] == "nile_corridor"
    assert body["aoi"] == [29.0, 24.0, 33.0, 32.0]
    assert body["start_month"] == "2005-01"
    assert body["end_month"] == "2020-12"
    assert body["period_months"] == 192


def test_receipt_carries_provenance_and_versions(client: TestClient, result: dict) -> None:
    body = client.get(f"/v1/receipts/{result['receipt_id']}").json()

    assert body["data_mode"] == "mock"
    assert body["provenance"]["mode"] == "mock"
    assert "No NASA product revision" in body["provenance"]["note"]
    assert body["provenance"]["statistics_adapter"] == "MockStatisticsAdapter"

    revision = body["dataset_revisions"][0]
    assert revision["product_id"] == "M2TMNXSLV"
    assert revision["version"] == "5.12.4"
    assert revision["source"] == "mock_registry_snapshot"

    assert body["method"]["method_version"]
    assert body["method"]["approved"] is False
    assert body["content_hash"]
    assert len(body["content_hash"]) == 64


def test_receipt_warnings_match_result(client: TestClient, result: dict) -> None:
    body = client.get(f"/v1/receipts/{result['receipt_id']}").json()
    assert {warning["code"] for warning in body["warnings"]} == {
        warning["code"] for warning in result["warnings"]
    }


def test_receipt_content_hash_is_stable(client: TestClient, result: dict) -> None:
    first = client.get(f"/v1/receipts/{result['receipt_id']}").json()
    second = client.get(f"/v1/receipts/{result['receipt_id']}").json()
    assert first["content_hash"] == second["content_hash"]
    assert first == second


def test_receipt_download_is_a_json_attachment(client: TestClient, result: dict) -> None:
    receipt_id = result["receipt_id"]
    response = client.get(f"/v1/receipts/{receipt_id}/download")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.headers["content-disposition"] == f'attachment; filename="{receipt_id}.json"'
    assert response.headers["X-Receipt-Content-Hash"]


def test_download_matches_receipt_endpoint(client: TestClient, result: dict) -> None:
    receipt_id = result["receipt_id"]
    served = client.get(f"/v1/receipts/{receipt_id}").json()
    downloaded = json.loads(client.get(f"/v1/receipts/{receipt_id}/download").content)
    assert downloaded == served


def test_unknown_receipt_returns_404(client: TestClient) -> None:
    response = client.get("/v1/receipts/receipt_mock_missing")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RECEIPT_NOT_FOUND"


def test_unknown_receipt_download_returns_404(client: TestClient) -> None:
    response = client.get("/v1/receipts/receipt_mock_missing/download")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RECEIPT_NOT_FOUND"


def test_receipt_exists_for_every_result(client: TestClient, analysis_payload: dict) -> None:
    payload = {**analysis_payload, "variable_ids": ["precipitation"]}
    created = client.post("/v1/analyses", json=payload).json()
    result = client.get(f"/v1/results/{created['result_id']}").json()
    receipt = client.get(f"/v1/receipts/{result['receipt_id']}")
    assert receipt.status_code == 200
    assert receipt.json()["variable_ids"] == ["precipitation"]

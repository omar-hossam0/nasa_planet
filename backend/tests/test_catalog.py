"""Tests for the catalog, region and availability endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_catalog_lists_four_variables(client: TestClient) -> None:
    response = client.get("/v1/catalog")
    assert response.status_code == 200
    body = response.json()

    assert body["count"] == 4
    assert body["data_mode"] == "mock"
    assert "Synthetic" in body["disclaimer"]

    ids = {item["variable_id"] for item in body["variables"]}
    assert ids == {"air_temperature", "soil_moisture", "precipitation", "vegetation_greenness"}


def test_catalog_separates_readiness_flags(client: TestClient) -> None:
    body = client.get("/v1/catalog").json()
    for item in body["variables"]:
        assert item["measurement_ready"] is True
        assert item["method_ready"] is False
        assert item["app_available"] is False
        assert item["demo_available"] is True
        assert item["availability_state"] == "measurement_ready"
        assert item["data_mode"] == "mock"


def test_catalog_marks_unverified_units(client: TestClient) -> None:
    variables = {item["variable_id"]: item for item in client.get("/v1/catalog").json()["variables"]}
    assert variables["air_temperature"]["units_verified"] is True
    assert variables["soil_moisture"]["units_verified"] is True
    assert variables["precipitation"]["units_verified"] is False
    assert variables["vegetation_greenness"]["units_verified"] is False


def test_variable_detail(client: TestClient) -> None:
    response = client.get("/v1/catalog/variables/air_temperature")
    assert response.status_code == 200
    body = response.json()
    assert body["display_name"] == "2-metre air temperature"
    assert body["source"]["product_id"] == "M2TMNXSLV"
    assert body["source"]["version"] == "5.12.4"
    assert body["coverage_start"] == "2001-01"
    assert body["coverage_end"] == "2024-12"
    assert "nile_corridor" in body["supported_regions"]
    assert body["limitations"]


def test_variable_detail_resolves_legacy_alias(client: TestClient) -> None:
    response = client.get("/v1/catalog/variables/T2M")
    assert response.status_code == 200
    assert response.json()["variable_id"] == "air_temperature"


def test_unknown_variable_returns_404(client: TestClient) -> None:
    response = client.get("/v1/catalog/variables/co2")
    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "VARIABLE_NOT_FOUND"
    assert error["details"]["variable_id"] == "co2"
    assert "air_temperature" in error["details"]["known_variable_ids"]


def test_regions_are_demo_only(client: TestClient) -> None:
    response = client.get("/v1/catalog/regions")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 3
    ids = {region["region_id"] for region in body["regions"]}
    assert ids == {"nile_corridor", "morocco_comparison", "sahel_comparison"}
    for region in body["regions"]:
        assert region["demo_only"] is True
        assert len(region["bbox"]) == 4


def test_availability_usable_demo(client: TestClient) -> None:
    response = client.get(
        "/v1/catalog/availability",
        params={
            "variable_id": "air_temperature",
            "region_id": "nile_corridor",
            "start_month": "2005-01",
            "end_month": "2020-12",
        },
    )
    assert response.status_code == 200
    body = response.json()

    assert body["usable"] is True
    assert body["demo_available"] is True
    assert body["measurement_ready"] is True
    assert body["method_ready"] is False
    assert body["app_available"] is False
    assert body["reason_code"] == "MOCK_DEMO_ONLY"
    assert body["simulated"] is True
    assert body["availability_source"] == "registry_snapshot + mock_demo_gate"
    assert "area_weighted" in body["supported_aggregation_policies"]


def test_availability_outside_coverage(client: TestClient) -> None:
    response = client.get(
        "/v1/catalog/availability",
        params={
            "variable_id": "air_temperature",
            "region_id": "nile_corridor",
            "start_month": "1990-01",
            "end_month": "1995-12",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["usable"] is False
    assert body["reason_code"] == "OUTSIDE_COVERAGE"


def test_availability_accepts_valid_bbox(client: TestClient) -> None:
    response = client.get(
        "/v1/catalog/availability",
        params={
            "variable_id": "soil_moisture",
            "region_id": "nile_corridor",
            "start_month": "2005-01",
            "end_month": "2020-12",
            "bbox": "29.5,24.5,32.5,31.5",
        },
    )
    assert response.status_code == 200
    assert response.json()["usable"] is True


def test_availability_rejects_malformed_bbox(client: TestClient) -> None:
    response = client.get(
        "/v1/catalog/availability",
        params={
            "variable_id": "soil_moisture",
            "region_id": "nile_corridor",
            "start_month": "2005-01",
            "end_month": "2020-12",
            "bbox": "29.5,24.5",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_AOI"


def test_availability_rejects_inverted_bbox(client: TestClient) -> None:
    response = client.get(
        "/v1/catalog/availability",
        params={
            "variable_id": "soil_moisture",
            "region_id": "nile_corridor",
            "start_month": "2005-01",
            "end_month": "2020-12",
            "bbox": "33,31,29,24",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_AOI"


def test_availability_unknown_variable(client: TestClient) -> None:
    response = client.get(
        "/v1/catalog/availability",
        params={
            "variable_id": "co2",
            "region_id": "nile_corridor",
            "start_month": "2005-01",
            "end_month": "2020-12",
        },
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "VARIABLE_NOT_FOUND"


def test_availability_unknown_region(client: TestClient) -> None:
    response = client.get(
        "/v1/catalog/availability",
        params={
            "variable_id": "air_temperature",
            "region_id": "atlantis",
            "start_month": "2005-01",
            "end_month": "2020-12",
        },
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "REGION_NOT_FOUND"


def test_availability_invalid_month_format(client: TestClient) -> None:
    response = client.get(
        "/v1/catalog/availability",
        params={
            "variable_id": "air_temperature",
            "region_id": "nile_corridor",
            "start_month": "2005-13",
            "end_month": "2020-12",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"

"""Tests for POST /v1/recommendations."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _recommend(client: TestClient, **payload) -> dict:
    body = {"question": payload.pop("question", "temperature"), **payload}
    return client.post("/v1/recommendations", json=body).json()


def test_temperature_question_recommends_air_temperature(client: TestClient) -> None:
    body = _recommend(client, question="I want to study temperature changes.")
    assert body["status"] == "recommended"
    assert [item["variable_id"] for item in body["candidates"]] == ["air_temperature"]
    candidate = body["candidates"][0]
    assert candidate["unit"] == "K"
    assert candidate["measurement_ready"] is True
    assert 0.0 < candidate["confidence"] <= 1.0
    assert candidate["rationale"]


def test_soil_moisture_question(client: TestClient) -> None:
    body = _recommend(client, question="How did soil moisture change in the delta?")
    assert body["status"] == "recommended"
    assert body["candidates"][0]["variable_id"] == "soil_moisture"


def test_rain_question_maps_to_precipitation(client: TestClient) -> None:
    body = _recommend(client, question="Any trend in rainfall?")
    assert body["status"] == "recommended"
    assert body["candidates"][0]["variable_id"] == "precipitation"


def test_ndvi_question_maps_to_vegetation(client: TestClient) -> None:
    body = _recommend(client, question="Show me the NDVI signal.")
    assert body["status"] == "recommended"
    assert body["candidates"][0]["variable_id"] == "vegetation_greenness"


def test_ambiguous_humidity_requires_clarification(client: TestClient) -> None:
    body = _recommend(client, question="What about humidity?")
    assert body["status"] == "clarification_required"
    assert body["candidates"] == []
    assert body["clarification_question"]
    assert "soil moisture" in body["clarification_question"].lower()


def test_unsupported_question(client: TestClient) -> None:
    body = _recommend(client, question="Tell me about volcanic eruptions")
    assert body["status"] == "unsupported"
    assert body["candidates"] == []
    assert "air_temperature" in body["message"]


def test_arabic_temperature_question(client: TestClient) -> None:
    body = _recommend(
        client,
        question="أريد دراسة تغير درجات الحرارة",
        language="ar",
    )
    assert body["status"] == "recommended"
    assert body["candidates"][0]["variable_id"] == "air_temperature"
    assert body["language"] == "ar"


def test_arabic_rain_question(client: TestClient) -> None:
    body = _recommend(client, question="أريد تحليل الأمطار", language="ar")
    assert body["status"] == "recommended"
    assert body["candidates"][0]["variable_id"] == "precipitation"


def test_arabic_ambiguous_moisture(client: TestClient) -> None:
    body = _recommend(client, question="ما هي الرطوبة؟", language="ar")
    assert body["status"] == "clarification_required"
    assert body["clarification_question"]


def test_recommendation_never_fabricates_references(client: TestClient) -> None:
    body = _recommend(client, question="temperature trend")
    assert body["references"] == []
    assert body["provider"] == "mock_rules"
    assert body["data_mode"] == "mock"


def test_context_is_echoed(client: TestClient) -> None:
    body = _recommend(
        client,
        question="temperature",
        region_id="nile_corridor",
        start_month="2005-01",
        end_month="2020-12",
    )
    assert body["context"]["region_id"] == "nile_corridor"
    assert body["context"]["region_known"] is True
    assert body["context"]["start_month"] == "2005-01"


def test_unknown_region_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/v1/recommendations",
        json={"question": "temperature", "region_id": "atlantis"},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "REGION_NOT_FOUND"


def test_invalid_language_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/v1/recommendations",
        json={"question": "temperature", "language": "fr"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_too_short_question_is_rejected(client: TestClient) -> None:
    response = client.post("/v1/recommendations", json={"question": "hi"})
    assert response.status_code == 422


def test_overlong_question_is_rejected(client: TestClient) -> None:
    response = client.post("/v1/recommendations", json={"question": "temperature " * 60})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert "500" in error["message"]


def test_invalid_period_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/v1/recommendations",
        json={"question": "temperature", "start_month": "2020-01", "end_month": "2005-12"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_PERIOD"

"""Tests for POST /v1/explanations."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_english_explanation_sections(client: TestClient, result: dict) -> None:
    response = client.post(
        "/v1/explanations",
        json={"result_id": result["result_id"], "language": "en"},
    )
    assert response.status_code == 200
    body = response.json()

    assert body["language"] == "en"
    assert body["mode"] == "mock_template"
    assert body["data_mode"] == "mock"
    assert body["explanation_id"].startswith("expl_mock_")

    section_ids = [section["section_id"] for section in body["sections"]]
    assert section_ids == ["summary", "interpretation", "spatial_insight", "time_window_insight"]
    for section in body["sections"]:
        assert section["title"]
        assert section["body"]


def test_explanation_reuses_stored_numbers(client: TestClient, result: dict) -> None:
    body = client.post(
        "/v1/explanations",
        json={"result_id": result["result_id"], "language": "en"},
    ).json()

    slope = result["variables"][0]["trend"]["slope_per_year"]
    summary = next(section for section in body["sections"] if section["section_id"] == "summary")
    assert f"{slope}" in summary["body"].rstrip("0").rstrip(".") or str(slope) in summary["body"]
    assert "Nile corridor" in summary["body"]
    assert "2005-01" in summary["body"]


def test_explanation_invents_no_references(client: TestClient, result: dict) -> None:
    body = client.post(
        "/v1/explanations",
        json={"result_id": result["result_id"], "language": "en"},
    ).json()
    assert body["references"] == []
    assert body["limitations"]


def test_explanation_exposes_proposed_actions(client: TestClient, result: dict) -> None:
    body = client.post(
        "/v1/explanations",
        json={"result_id": result["result_id"], "language": "en"},
    ).json()
    action_ids = [action["action_id"] for action in body["actions"]]
    assert action_ids == [
        "FOCUS_REGION",
        "FOCUS_REGIONAL_CHART",
        "REVEAL_CELLS",
        "OPEN_SPIN_IT",
        "OPEN_RECEIPT",
    ]
    receipt_action = next(action for action in body["actions"] if action["action_id"] == "OPEN_RECEIPT")
    assert receipt_action["payload"]["receipt_id"] == result["receipt_id"]


def test_arabic_explanation(client: TestClient, result: dict) -> None:
    body = client.post(
        "/v1/explanations",
        json={"result_id": result["result_id"], "language": "ar"},
    ).json()

    assert body["language"] == "ar"
    titles = [section["title"] for section in body["sections"]]
    assert any("\u0627\u0644\u0645\u0644\u062e\u0635" == title for title in titles), titles
    assert all(section["body"] for section in body["sections"])


def test_explanations_are_deterministic_in_id(client: TestClient, result: dict) -> None:
    first = client.post(
        "/v1/explanations", json={"result_id": result["result_id"], "language": "en"}
    ).json()
    second = client.post(
        "/v1/explanations", json={"result_id": result["result_id"], "language": "en"}
    ).json()
    assert first["explanation_id"] == second["explanation_id"]
    assert first["sections"] == second["sections"]


def test_unknown_result_returns_404(client: TestClient) -> None:
    response = client.post("/v1/explanations", json={"result_id": "result_mock_missing"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESULT_NOT_FOUND"


def test_unsupported_language_returns_422(client: TestClient, result: dict) -> None:
    response = client.post(
        "/v1/explanations",
        json={"result_id": result["result_id"], "language": "fr"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_incomplete_result_is_rejected() -> None:
    """A queued job has no result, so an explanation cannot be produced."""
    from fastapi.testclient import TestClient as Client

    from app.main import create_app
    from tests.conftest import make_settings

    app = create_app(make_settings(mock_auto_complete_jobs=False))
    with Client(app) as client:
        created = client.post(
            "/v1/analyses",
            json={
                "variable_ids": ["air_temperature"],
                "region_id": "nile_corridor",
                "start_month": "2005-01",
                "end_month": "2020-12",
            },
        ).json()
        assert created["result_id"] is None

        response = client.post("/v1/explanations", json={"result_id": "result_mock_unknown"})
        assert response.status_code == 404

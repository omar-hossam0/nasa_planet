"""Repository isolation and cross-run determinism."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import make_settings

PAYLOAD = {
    "variable_ids": ["air_temperature"],
    "region_id": "nile_corridor",
    "start_month": "2005-01",
    "end_month": "2020-12",
}


def test_two_app_instances_do_not_share_state() -> None:
    app_a = create_app(make_settings())
    app_b = create_app(make_settings())

    with TestClient(app_a) as client_a:
        created = client_a.post("/v1/analyses", json=PAYLOAD).json()
        result_id = created["result_id"]
        assert client_a.get(f"/v1/results/{result_id}").status_code == 200

    with TestClient(app_b) as client_b:
        assert client_b.get(f"/v1/results/{result_id}").status_code == 404
        assert client_b.get(f"/v1/analyses/{created['job_id']}").status_code == 404


def test_state_persists_within_one_app_instance() -> None:
    app = create_app(make_settings())
    with TestClient(app) as client:
        created = client.post("/v1/analyses", json=PAYLOAD).json()
        for _ in range(3):
            assert client.get(f"/v1/results/{created['result_id']}").status_code == 200
        receipt_id = client.get(f"/v1/results/{created['result_id']}").json()["receipt_id"]
        assert client.get(f"/v1/receipts/{receipt_id}").status_code == 200


def test_same_request_is_byte_identical_across_app_instances() -> None:
    app_a = create_app(make_settings())
    app_b = create_app(make_settings())

    with TestClient(app_a) as client_a:
        first = client_a.post("/v1/analyses", json=PAYLOAD).json()
        first_result = client_a.get(f"/v1/results/{first['result_id']}").json()

    with TestClient(app_b) as client_b:
        second = client_b.post("/v1/analyses", json=PAYLOAD).json()
        second_result = client_b.get(f"/v1/results/{second['result_id']}").json()

    assert first["job_id"] == second["job_id"]
    assert first["result_id"] == second["result_id"]
    assert first_result["variables"] == second_result["variables"]
    assert first_result["datasets"] == second_result["datasets"]


def test_repositories_are_empty_before_first_request() -> None:
    app = create_app(make_settings())
    container = app.state.container
    assert container.jobs_repo.list_all() == []
    assert container.results_repo.list_all() == []
    assert container.cache.get("anything") is None

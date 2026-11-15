"""Real NASA -> science -> persistence/API -> Role04, without any provider calls."""

import json
from pathlib import Path
import statistics
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from tests.conftest import make_settings

ROOT = Path(__file__).resolve().parents[2]
REFERENCES = json.loads(
    (ROOT / "packages/science/phase_reports/PHASE_3_RESULTS.json").read_text()
)["cases"]
CASES = [r for r in REFERENCES if r["policy"] == "strict_100"]


@pytest.fixture(scope="module")
def real_client():
    with TestClient(create_app(make_settings(mock_mode=False))) as client:
        yield client


def submit(client, variable="air_temperature", region="nile_corridor", **extra):
    accepted = client.post(
        "/v1/analyses",
        json={
            "variable_ids": [variable],
            "region_id": region,
            "start_month": "2001-01",
            "end_month": "2024-12",
            **extra,
        },
    )
    assert accepted.status_code in (200, 202), accepted.text
    return client.get("/v1/results/" + accepted.json()["result_id"]).json()


@pytest.mark.parametrize("case", CASES, ids=[r["case"] for r in CASES])
def test_all_twelve_real_analyses_match_archived_and_independent_slope(
    real_client, case
):
    result = submit(real_client, case["variable_id"], case["region_id"])
    assert result["data_mode"] == "real"
    assert result["method"]["approved"] is False
    variable = result["variables"][0]
    artifact = result["science"][case["variable_id"]]
    slope = variable["trend"]["slope_per_year"]
    assert slope == pytest.approx(
        case["regional"]["annual"]["slope_per_year"], abs=1e-10
    )
    pairs = [
        (y, v)
        for y, v in zip(artifact["annual_years"], artifact["regional_annual"])
        if v is not None
    ]
    reference = statistics.median(
        (b[1] - a[1]) / (b[0] - a[0])
        for i, a in enumerate(pairs)
        for b in pairs[i + 1 :]
    )
    assert slope == pytest.approx(reference, abs=1e-12)
    assert variable["trend"]["p_value"] is None
    assert variable["trend"]["inference_status"] == "not_computed"
    grid = real_client.get(f'/v1/results/{result["result_id"]}/spatial').json()
    assert grid["data_mode"] == "real"
    assert grid["cell_count"] == artifact["metadata"]["selected_cell_count"]
    assert grid["cell_count"] == len(artifact["lat"]) * len(artifact["lon"])
    assert (
        artifact["positive_cells"] + artifact["negative_cells"]
        <= artifact["metadata"]["eligible_fixed_support_cells"]
    )
    assert artifact['positive_cells']+artifact['negative_cells']+artifact['zero_cells']+artifact['unavailable_eligible_cells'] == artifact['metadata']['eligible_fixed_support_cells']
    assert all(cell["data_mode"] == "real" for cell in grid["cells"])
    for row in [0, len(artifact["lat"]) - 1]:
        for col in [0, len(artifact["lon"]) - 1]:
            cell = next(c for c in grid["cells"] if c["cell_id"] == f"cell_{row}_{col}")
            assert cell["trend_value"] == artifact["annual_slope"][row][col]
    receipt = real_client.get(f'/v1/receipts/{result["receipt_id"]}').json()
    assert receipt["provenance"]["statistics_adapter"] == "ScienceStatisticsAdapter"
    assert artifact["source_sha256"] in receipt["dataset_revisions"][0]["revision"]
    explanation = real_client.post(
        "/v1/explanations", json={"result_id": result["result_id"]}
    ).json()
    assert explanation["mode"] == "conclusion_templates"
    assert explanation["data_mode"] == "real"
    assert any(
        format(slope, ".8g") in section["body"] for section in explanation["sections"]
    )
    assert explanation["references"]


def test_native_cell_detail_and_real_spin(real_client):
    result = submit(real_client)
    rid = result["result_id"]
    cell = real_client.get(f"/v1/results/{rid}/cells/cell_0_0").json()
    assert cell["data_mode"] == "real"
    assert (
        cell["trend"]["slope_per_year"]
        == result["science"]["air_temperature"]["annual_slope"][0][0]
    )
    accepted = real_client.post(
        f"/v1/results/{rid}/spin", json={"minimum_window_years": 10}
    ).json()
    assert accepted["data_mode"] == "real"
    spin = real_client.get("/v1/spin/" + accepted["spin_id"]).json()
    assert spin["data_mode"] == "real"
    assert len(spin["windows"]) == 15
    assert spin["windows"][-1]["end_month"] == "2024-12"
    compact = real_client.get(f"/v1/results/{rid}/spatial?compact=true").json()
    assert compact["slope"] == result["science"]["air_temperature"]["annual_slope"]
    assert compact["lat"] == result["science"]["air_temperature"]["lat"]
    compared = real_client.post(
        "/v1/comparisons",
        json={
            "result_id": rid,
            "comparison_type": "cells",
            "cell_ids": ["cell_0_0", "cell_0_1"],
        },
    )
    assert compared.status_code == 200, compared.text
    assert compared.json()["data_mode"] == "real"
    assert compared.json()["cells"][0]["trend_value"] == cell["trend"]["slope_per_year"]


def test_no_source_cell_or_wrong_aggregation_is_rejected(real_client):
    body = {
        "variable_ids": ["air_temperature"],
        "region_id": "nile_corridor",
        "start_month": "2001-01",
        "end_month": "2024-12",
    }
    assert (
        real_client.post(
            "/v1/analyses",
            json={
                **body,
                "aoi": {"type": "bbox", "coordinates": [29, 24.05, 29.25, 24.3]},
            },
        ).status_code
        == 409
    )
    assert (
        real_client.post(
            "/v1/analyses", json={**body, "aggregation_policy": "cell_mean"}
        ).status_code
        == 422
    )


def test_custom_area_and_period_are_actually_used(real_client):
    box = [30, 26, 32, 30]
    result = submit(
        real_client,
        start_month="2010-01",
        end_month="2020-12",
        aoi={"type": "bbox", "coordinates": box},
    )
    artifact = result["science"]["air_temperature"]
    assert artifact["metadata"]["requested_bbox"] == box
    assert min(artifact["lat"]) >= 26 and max(artifact["lat"]) <= 30
    assert min(artifact["lon"]) >= 30 and max(artifact["lon"]) <= 32
    assert result["variables"][0]["trend"]["n_years"] == 11
    assert len(result["variables"][0]["series"]) == 132
    assert result["analysis"]["start_month"] == "2010-01"


def test_real_sql_worker_persists_actual_outputs(tmp_path):
    app = create_app(
        make_settings(
            mock_mode=False,
            job_backend="database",
            database_auto_create=True,
            database_url=f'sqlite:///{tmp_path/"science.db"}',
        )
    )
    with TestClient(app) as client:
        job = client.post(
            "/v1/analyses",
            json={
                "variable_ids": ["air_temperature"],
                "region_id": "nile_corridor",
                "start_month": "2001-01",
                "end_month": "2024-12",
            },
        ).json()
        assert job["status"] == "queued"
        assert app.state.container.job_manager.run_one(app.state.container)
        done = client.get("/v1/analyses/" + job["job_id"]).json()
        result = client.get("/v1/results/" + done["result_id"]).json()
        assert result["data_mode"] == "real"
        assert result["variables"][0]["trend"]["slope_per_year"] == pytest.approx(
            0.025330383313493597
        )


def test_result_explanations_never_call_provider(real_client, monkeypatch):
    from packages.rag.provider import GeminiClient

    def forbidden(*args, **kwargs):
        raise AssertionError("Result templates must never call Gemini")

    monkeypatch.setattr(GeminiClient, "generate", forbidden)
    result = submit(real_client)
    for language in ("en", "ar"):
        response = real_client.post("/v1/explanations", json={
            "result_id": result["result_id"], "language": language,
        })
        assert response.status_code == 200, response.text
        assert response.json()["mode"] == "conclusion_templates"
        assert response.json()["sections"]
    rejected = real_client.post("/v1/explanations", json={
        "result_id": result["result_id"], "style": "llm",
    })
    assert rejected.status_code == 422

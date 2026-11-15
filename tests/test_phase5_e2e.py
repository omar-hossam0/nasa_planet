import copy
import json
import os
import pathlib
import re
import socket
import subprocess

import pytest

from packages.rag.conclusions import PERMITTED_ACTIONS, PayloadError
from packages.rag.facade import Role04Service, normalize_result_payload

ROOT = pathlib.Path(__file__).resolve().parents[1]

REGIONS = ["nile_corridor", "morocco_comparison", "sahel_comparison"]
VARIABLES = ["air_temperature", "soil_moisture", "precipitation", "vegetation_greenness"]
PERIOD = ("2001-01", "2024-12")

QUESTION_BY_VARIABLE = {
    "air_temperature": "temperature trend",
    "soil_moisture": "soil moisture trend",
    "precipitation": "rainfall trend",
    "vegetation_greenness": "vegetation greenness trend",
}

PRODUCT_FAMILY = {
    "air_temperature": {"M2TMNXSLV", "MERRA2_README", "MERRA2_Specification", "MERRA2_Reprocessing"},
    "soil_moisture": {"GLDAS_NOAH025_M", "GLDAS", "GLDAS_Models"},
    "precipitation": {"GPM_3IMERGM", "IMERG_V07_ATBD"},
    "vegetation_greenness": {"MOD13C2", "MOD13_User_Guide_V61"},
}

UNITS = {
    "air_temperature": "K",
    "soil_moisture": "kg m-2",
    "precipitation": "mm",
    "vegetation_greenness": "NDVI index",
}
MEANS = {
    "air_temperature": 295.31,
    "soil_moisture": 42.7,
    "precipitation": 12.4,
    "vegetation_greenness": 0.312,
}
SLOPES = {
    "air_temperature": (0.021, "K per year"),
    "soil_moisture": (-0.034, "kg m-2 per year"),
    "precipitation": (0.007, "mm per year"),
    "vegetation_greenness": (0.0004, "NDVI per year"),
}

BANNED_WORDS = ["stable", "unchanged", "no change", "ثابت", "مستقر", "truly"]
NULL_LITERAL_RE = re.compile(r"\b(None|null|NaN)\b")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


class KeylessProvider:
    def is_configured(self):
        return False


@pytest.fixture(scope="module")
def service():
    return Role04Service(provider=KeylessProvider())


def result_payload_for(service, variable, region, analysis_id="an_2026_001", request_id="req_2026_001"):
    lookup = service.retriever.readiness.lookup(variable, region, PERIOD)
    assert lookup["found"] is True
    slope, slope_units = SLOPES[variable]
    ci_low, ci_high = sorted((slope * 0.6, slope * 1.4))
    return {
        "analysis_id": analysis_id,
        "request_id": request_id,
        "region_id": region,
        "variable_id": variable,
        "period": {"start_month": PERIOD[0], "end_month": PERIOD[1]},
        "units": UNITS[variable],
        "result_state": "succeeded",
        "product": {"product_id": lookup["product_id"], "product_version": lookup["product_version"]},
        "regional": {
            "mean": MEANS[variable],
            "n_months": 288,
            "sen_slope": slope,
            "slope_units": slope_units,
            "p_value": 0.03,
            "significance_alpha": 0.05,
            "confidence_interval": {"low": ci_low, "high": ci_high},
        },
        "method_revision": "m2_sen_mk_hamed_rao_v1",
        "data_revision": lookup["data_revision"],
        "cells": {
            "denominator": "eligible_cells",
            "total_cells": 960,
            "eligible_cells": 950,
            "ineligible_qa_cells": 10,
            "increasing_cells": 200,
            "decreasing_cells": 40,
            "non_significant_cells": 710,
        },
        "coverage": {"valid_area_fraction": 0.98, "denominator": "weighted_area", "ineligible_cells": 10},
        "sensitivity": {"matching_windows": 3, "total_windows": 5},
        "artifacts": {"regional_chart": True, "cell_reveal": True, "spin_it": True, "receipt": True},
        "receipt_id": "rc_2026_001",
    }


def assert_clean_texts(result):
    segments = result.get("segments")
    texts = [s["text"] for s in segments] if segments else []
    if not segments:
        texts = [n["text"] for n in result.get("notes", []) if isinstance(n, dict) and "text" in n]
        texts.extend(result.get("limitations", []))
    for text in texts:
        lowered = text.lower()
        for banned in BANNED_WORDS:
            assert banned.lower() not in lowered, (banned, text)
        assert not NULL_LITERAL_RE.search(text), text


@pytest.mark.parametrize("variable", VARIABLES)
@pytest.mark.parametrize("region", REGIONS)
def test_real_data_e2e_all_variables_all_regions(service, variable, region):
    service.reset_session()
    answer = service.answer_question(
        QUESTION_BY_VARIABLE[variable], region_id=region, period=PERIOD
    )
    assert answer["mode"] == "local_retrieval"
    assert answer["status"] == "documented_only"
    assert answer["reason_code"] == "measurement_ready_app_not_available"
    assert answer["variable_ids"] == [variable]

    lookup = service.retriever.readiness.lookup(variable, region, PERIOD)
    assert lookup["found"] is True
    assert lookup["measurement_ready"] is True
    assert lookup["data_revision"]

    assert answer["citations"]
    seen_products = set()
    for citation in answer["citations"]:
        assert HEX64_RE.match(citation["raw_source_hash"]), citation["chunk_id"]
        assert citation["source_url"].startswith("https://")
        assert citation["source_kind"] in ("product_doc", "method_doc")
        if citation["product_id"]:
            seen_products.add(citation["product_id"])
            if citation["product_id"] == lookup["product_id"]:
                assert citation["product_version"] == lookup["product_version"], citation["chunk_id"]
    assert seen_products & PRODUCT_FAMILY[variable], seen_products

    payload = result_payload_for(service, variable, region)
    identity = service.register_analysis(payload)
    assert identity["region_id"] == region
    en = service.render_result(payload, "en")
    ar = service.render_result(payload, "ar")
    for rendered in (en, ar):
        assert rendered["status"] == "succeeded"
        assert rendered["mode"] == "conclusion_templates"
        assert len(rendered["segments"]) >= 5
        assert {a["action"] for s in rendered["segments"] for a in s["actions"]} <= PERMITTED_ACTIONS
        assert_clean_texts(rendered)
    assert [s["id"] for s in en["segments"]] == [s["id"] for s in ar["segments"]]
    numbers = re.compile(r"\d+(?:\.\d+)?")
    assert (
        set(numbers.findall(" ".join(s["text"] for s in en["segments"])))
        == set(numbers.findall(" ".join(s["text"] for s in ar["segments"])))
    )


EVAL_EXPECTATIONS = {
    "هل الدلتا بتسخن؟": (["air_temperature"], "documented_only"),
    "رطوبة التربة نسبتها كام؟": (["soil_moisture"], "documented_only"),
    "ليه الحرارة زادت؟": (["air_temperature"], "documented_only"),
    "هل MERRA-2 قياسات محطة؟": (["air_temperature"], "documented_only"),
    "هل GLDAS قياس مباشر؟": (["soil_moisture"], "documented_only"),
    "الدلالة 0.03 معناها الاستنتاج صح بنسبة 97%؟": ([], "unsupported"),
    "هات اتجاه حي مدينة نصر": ([], "unsupported"),
    "احسب الاتجاه من 1990": ([], "unavailable"),
    "هل رطوبة التربة متاحة دلوقتي؟": (["soil_moisture"], "documented_only"),
    "اختيار فترة قصيرة يغيّر الاتجاه؟": ([], "unsupported"),
    "هل أقدر أقارن خليتين من شبكتين مختلفتين مباشرة؟": ([], "unsupported"),
    "اعمل خريطة دلالة لكل الخلايا": ([], "unsupported"),
}


def test_evaluation_dataset_end_to_end(service):
    questions = json.loads((ROOT / "data/nasa/rag/evaluation_questions.json").read_text(encoding="utf-8"))
    assert len(questions) == 12
    for item in questions:
        question = item["question"]
        assert question in EVAL_EXPECTATIONS, question
        expected_variables, expected_status = EVAL_EXPECTATIONS[question]
        result = service.answer_question(question)
        assert result["mode"] == "local_retrieval", question
        assert result["status"] == expected_status, (question, result["status"])
        assert result["variable_ids"] == expected_variables, question
        assert_clean_texts(result)


def test_offline_keyless_full_flow_with_network_disabled(service, monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("network access attempted during keyless operation")

    monkeypatch.setattr(socket, "socket", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    answer = service.answer_question("هل الدلتا بتسخن؟", region_id="nile_corridor", period=PERIOD)
    assert answer["mode"] == "local_retrieval"
    assert answer["fallback_reason"] == "provider_not_configured"
    assert answer["citations"]

    payload = result_payload_for(service, "air_temperature", "nile_corridor")
    service.register_analysis(payload)
    rendered = service.render_result(payload, "ar")
    assert rendered["status"] == "succeeded"
    assert rendered["segments"]
    assert_clean_texts(rendered)


def test_role03_payload_adapter_equivalence(service):
    service.reset_session()
    role03_style = {
        "result_id": "an_2026_001",
        "request_hash": "req_2026_001",
        "region_id": "nile_corridor",
        "variable_id": "air_temperature",
        "start_month": "2001-01",
        "end_month": "2024-12",
        "units": "K",
        "state": "succeeded",
        "source": {"product_id": "M2TMNXSLV", "product_version": "5.12.4"},
        "regional_mean": 295.31,
        "n_months": 288,
        "slope": 0.021,
        "slope_units": "K per year",
        "p": 0.03,
        "alpha": 0.05,
        "ci": {"low": 0.0126, "high": 0.0294},
        "method_revision": "m2_sen_mk_hamed_rao_v1",
        "cell_distribution": {
            "denominator": "eligible_cells",
            "total": 960,
            "eligible": 950,
            "masked_cells": 10,
            "increasing": 200,
            "decreasing": 40,
            "non_significant": 710,
        },
        "qa_coverage": {"valid_fraction": 0.98, "denominator": "weighted_area", "masked_cells": 10},
        "spin_it_summary": {"agreeing_windows": 3, "windows": 5},
        "availability_flags": {"chart": True, "cells": True, "spin_it": True, "receipt": True},
        "receipt": "rc_2026_001",
    }
    canonical = result_payload_for(service, "air_temperature", "nile_corridor")
    normalized = normalize_result_payload(role03_style)
    from_en = service.render_result(role03_style, "en", normalize=True)
    from_canonical = service.render_result(canonical, "en", normalize=False)
    assert [s["id"] for s in from_en["segments"]] == [s["id"] for s in from_canonical["segments"]]
    assert [s["text"] for s in from_en["segments"]] == [s["text"] for s in from_canonical["segments"]]
    assert from_en["status"] == from_canonical["status"] == "succeeded"
    assert normalized["analysis_id"] == "an_2026_001"
    assert normalized["request_id"] == "req_2026_001"
    assert normalized["regional"]["sen_slope"] == 0.021
    assert normalized["regional"]["p_value"] == 0.03
    assert normalized["cells"]["ineligible_qa_cells"] == 10
    assert normalized["artifacts"] == {"regional_chart": True, "cell_reveal": True, "spin_it": True, "receipt": True}


def test_adapter_accepts_period_list_and_nested_period(service):
    service.reset_session()
    payload = {
        "analysis_id": "an_1",
        "request_id": "rq_1",
        "region_id": "nile_corridor",
        "variable_id": "precipitation",
        "units": "mm",
        "product": {"product_id": "GPM_3IMERGM", "product_version": "07"},
        "regional": {"mean": 12.4, "n_months": 288, "sen_slope": 0.007, "slope_units": "mm per year",
                     "p_value": 0.03, "significance_alpha": 0.05},
        "period": ["2001-01", "2024-12"],
    }
    rendered = service.render_result(payload, "en", normalize=True)
    assert rendered["period"] == {"start_month": "2001-01", "end_month": "2024-12"}
    assert rendered["status"] == "succeeded"


def test_adapter_missing_required_field_raises(service):
    payload = {"region_id": "nile_corridor", "variable_id": "precipitation"}
    with pytest.raises(PayloadError) as excinfo:
        service.render_result(payload, "en", normalize=True)
    assert any("missing required field analysis_id" in e for e in excinfo.value.errors)


def test_service_stale_protection_e2e(service):
    payload = result_payload_for(service, "air_temperature", "nile_corridor", "an_1", "rq_1")
    service.register_analysis(payload)
    assert service.render_result(payload, "en")["status"] == "succeeded"
    stale = copy.deepcopy(payload)
    stale["request_id"] = "rq_old"
    result = service.render_result(stale, "en")
    assert result["status"] == "stale_response"
    assert result["segments"] == [] and result["actions"] == []

    payload2 = result_payload_for(service, "soil_moisture", "sahel_comparison", "an_2", "rq_2")
    service.register_analysis(payload2)
    assert service.render_result(payload2, "en")["status"] == "succeeded"
    old_again = service.render_result(payload, "en")
    assert old_again["status"] == "stale_response"
    assert "superseded" in old_again["reason"]

    changed = copy.deepcopy(payload2)
    changed["period"] = {"start_month": "2005-01", "end_month": "2020-12"}
    assert service.render_result(changed, "en")["status"] == "stale_response"


def test_live_probe_skips_cleanly_without_key(monkeypatch, service):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    result = service.live_probe("هل الدلتا بتسخن؟")
    assert result["status"] == "skipped"
    assert "skipped" in result["reason"]
    assert result["mode"] == "skipped"


def _find_env_key():
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            stripped = line.strip()
            if stripped.startswith("GEMINI_API_KEY="):
                value = stripped.split("=", 1)[1].strip()
                if value:
                    return value
    return None


HAS_KEY = _find_env_key() is not None


@pytest.mark.skipif(not HAS_KEY, reason="GEMINI_API_KEY not configured; live probe skipped while all mock provider checks still run")
def test_live_gemini_probe_bounded(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", _find_env_key())
    live_service = Role04Service()
    result = live_service.live_probe(
        "هل الدلتا بتسخن؟", region_id="nile_corridor", period=PERIOD
    )
    assert result["mode"] in ("llm", "local_retrieval")
    assert result.get("probe_elapsed_seconds", 0) < 30
    if result["mode"] == "llm":
        assert result["validation"]["passed"] is True
        assert result["citations"]
    else:
        assert result.get("fallback_reason")


KEY_PATTERNS = [
    re.compile(r"AIza[0-9A-Za-z_\-]{20,}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"gsk_[A-Za-z0-9]{20,}"),
    re.compile(r"(?:GEMINI|MISTRAL)_API_KEY[ \t]*=[ \t]*[A-Za-z0-9_\-]{8,}"),
]
TEXT_SUFFIXES = {
    ".py", ".md", ".json", ".jsonl", ".txt", ".html", ".csv", ".ini", ".cfg",
    ".yaml", ".yml", ".toml", ".example", ".ps1", ".sh", ".js", ".ts", ".tsx",
}


def test_repository_secrets_audit_no_keys_or_env_files():
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=str(ROOT), capture_output=True, text=True, check=True
    ).stdout.splitlines()
    assert tracked, "git ls-files returned nothing; run inside the repository"
    assert ".env" not in tracked
    violations = []
    for relative in tracked:
        path = ROOT / relative
        if not path.is_file() or path.stat().st_size > 2_000_000:
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name != ".env.example":
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pattern in KEY_PATTERNS:
            match = pattern.search(content)
            if match:
                violations.append((relative, pattern.pattern))
    assert violations == [], f"potential secrets in tracked files: {violations}"


def test_env_example_key_is_empty_and_gitignore_excludes_env():
    example = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "GEMINI_API_KEY=\n" in example
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8", errors="ignore")
    assert ".env" in gitignore


def test_full_demo_sequence_smoke(service):
    service.reset_session()
    answers = [
        service.answer_question("هل الدلتا بتسخن؟", region_id="nile_corridor", period=PERIOD),
        service.answer_question("رطوبة التربة نسبتها كام؟"),
        service.answer_question("أمطار الصيف في الساحل", region_id="sahel_comparison", period=PERIOD),
    ]
    assert all(a["mode"] == "local_retrieval" for a in answers)
    assert answers[0]["variable_ids"] == ["air_temperature"]
    assert answers[1]["status"] == "documented_only"
    assert answers[2]["variable_ids"] == ["precipitation"]

    payloads = [
        result_payload_for(service, "air_temperature", "nile_corridor", "an_demo_1", "rq_demo_1"),
        result_payload_for(service, "precipitation", "sahel_comparison", "an_demo_2", "rq_demo_2"),
    ]
    for payload in payloads:
        service.register_analysis(payload)
        en = service.render_result(payload, "en")
        ar = service.render_result(payload, "ar")
        assert en["status"] == ar["status"] == "succeeded"
        assert [s["id"] for s in en["segments"]] == [s["id"] for s in ar["segments"]]
        assert_clean_texts(en)
    stale = service.render_result(payloads[0], "en")
    assert stale["status"] == "stale_response"

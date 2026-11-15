import json
import pathlib
import subprocess
import socket
import sys

import pytest

from packages.rag.retriever import Retriever, answer_query
from packages.rag.intent import (
    STATUS_RECOMMENDED,
    STATUS_DOCUMENTED_ONLY,
    STATUS_AMBIGUOUS,
    STATUS_UNSUPPORTED,
    STATUS_UNAVAILABLE,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]

EVAL_PATH = ROOT / "data/nasa/rag/evaluation_questions.json"


@pytest.fixture(scope="module")
def retriever():
    return Retriever()


def q(retriever, query, **kwargs):
    return retriever.answer_query(query, **kwargs)


VARIABLE_CASES = {
    "air_temperature": [
        "temperature trend",
        "Is the Delta warming?",
        "احسب اتجاه الحرارة",
        "درجة الحرارة في الوادي",
        "هل بيسخن في الصعيد؟",
    ],
    "soil_moisture": [
        "soil moisture trend",
        "soil wetness",
        "رطوبة التربة نسبتها كام؟",
        "اتجاه رطوبة التربة",
    ],
    "precipitation": [
        "rainfall trend",
        "precipitation",
        "مطر",
        "أمطار الصيف",
        "الامطار في الدلتا",
    ],
    "vegetation_greenness": [
        "NDVI trend",
        "vegetation greenness",
        "الغطاء النباتي",
        "اتجاه النباتات",
    ],
}


@pytest.mark.parametrize("variable,queries", sorted(VARIABLE_CASES.items()))
def test_unambiguous_synonyms_resolve(retriever, variable, queries):
    for query in queries:
        result = q(retriever, query)
        assert result["status"] in (STATUS_RECOMMENDED, STATUS_DOCUMENTED_ONLY), (query, result["status"])
        assert result["variable_ids"] == [variable], (query, result["variable_ids"])
        assert result["mode"] == "local_retrieval"


def test_diacritics_and_alef_variants(retriever):
    for query in [
        "الإمطار",
        "أمطار",
        "اَلْأَمْطَار",
        "الامطار",
        "إمطار",
    ]:
        result = q(retriever, query)
        assert result["variable_ids"] == ["precipitation"], query


def test_arabic_digits_and_punctuation_handling(retriever):
    res_arabic_year = q(retriever, "احسب حرارة الدلتا من ١٩٩٠")
    assert res_arabic_year["status"] == STATUS_UNAVAILABLE
    assert res_arabic_year["reason_code"] == "period_outside_scope"

    res_qmark = q(retriever, "هل الحرارة بتزيد؟")
    assert res_qmark["variable_ids"] == ["air_temperature"]

    res_kam = q(retriever, "رطوبة التربة كم؟")
    assert any(n["kind"] == "units_check" for n in res_kam["notes"])

    res_cause = q(retriever, "علشان ايه المطر قل؟")
    assert any(n["kind"] == "causality_guard" for n in res_cause["notes"])


def test_attached_prefixes(retriever):
    for query in ["والحرارة", "بالحرارة", "للأمطار", "فالنباتات", "بالامطار"]:
        result = q(retriever, query)
        assert result["variable_ids"] in (
            ["air_temperature"],
            ["precipitation"],
            ["vegetation_greenness"],
        ), query


def test_mixed_language_query(retriever):
    result = q(retriever, "اربط NDVI بالمطر في نفس الفترة")
    assert set(result["variable_ids"]) == {"vegetation_greenness", "precipitation"}
    result_en = q(retriever, "relate NDVI to rain over the same period")
    assert set(result_en["variable_ids"]) == {"vegetation_greenness", "precipitation"}


def test_winter_trap_never_maps_rain(retriever):
    result = q(retriever, "شتاء")
    assert result["status"] == STATUS_AMBIGUOUS
    assert result["reason_code"] == "season_without_variable"
    assert result["suggested_variable_ids"] == []
    assert "winter" in result["clarification"].lower()
    result_en = q(retriever, "winter")
    assert result_en["status"] == STATUS_AMBIGUOUS
    assert result_en["suggested_variable_ids"] == []
    result_cold = q(retriever, "برد الشتاء")
    assert result_cold["variable_ids"] == ["air_temperature"]
    assert "precipitation" not in result_cold["variable_ids"]


def test_humidity_trap_requires_clarification(retriever):
    for query in ["رطوبة", "الرطوبة", "humidity", "moisture"]:
        result = q(retriever, query)
        assert result["status"] == STATUS_AMBIGUOUS, query
        assert result["reason_code"] == "air_vs_soil_humidity"
        assert result["suggested_variable_ids"] == []
        lowered = result["clarification"].lower()
        assert "soil" in lowered or "التربة" in result["clarification"]
    qualified = q(retriever, "رطوبة التربة")
    assert qualified["variable_ids"] == ["soil_moisture"]
    air_qualified = q(retriever, "رطوبة الهواء")
    assert air_qualified["status"] == STATUS_UNSUPPORTED
    assert air_qualified["reason_code"] == "target_variable_not_available"


def test_temperature_air_vs_surface_clarification(retriever):
    result = q(retriever, "الحرارة في الدلتا")
    assert result["variable_ids"] == ["air_temperature"]
    kinds = [n["kind"] for n in result["notes"]]
    assert "clarification" in kinds


def test_empty_and_oversized_queries(retriever):
    empty = q(retriever, "")
    assert empty["status"] == STATUS_UNSUPPORTED
    assert empty["reason_code"] == "empty_query"
    whitespace = q(retriever, "   \n\t  ")
    assert whitespace["status"] == STATUS_UNSUPPORTED
    oversized = q(retriever, "climate " * 300)
    assert oversized["status"] == STATUS_UNSUPPORTED
    assert oversized["reason_code"] == "oversized_query"
    assert oversized["suggested_variable_ids"] == []


@pytest.mark.parametrize(
    "query",
    [
        "سرعة الرياح في القاهرة",
        "wind speed over the Sahel",
        "زلزال",
        "earthquake last week",
        "مستوى سطح البحر في الإسكندرية",
        "sea level rise",
        "الإشعاع الشمسي",
        "solar radiation trend",
    ],
)
def test_out_of_scope_topics_never_recommend(retriever, query):
    result = q(retriever, query)
    assert result["status"] == STATUS_UNSUPPORTED
    assert result["reason_code"] == "out_of_scope_topic"
    assert result["suggested_variable_ids"] == []
    assert result["citations"] == []


def test_low_confidence_gibberish_abstains(retriever):
    result = q(retriever, "xqzq جبرقبخس")
    assert result["status"] == STATUS_UNSUPPORTED
    assert result["reason_code"] == "no_target_variable_identified"
    assert result["suggested_variable_ids"] == []


def test_bilingual_intent_parity(retriever):
    family = {
        "air_temperature": {"M2TMNXSLV", "MERRA2_README", "MERRA2_Specification", "MERRA2_Reprocessing"},
        "soil_moisture": {"GLDAS_NOAH025_M", "GLDAS", "GLDAS_Models"},
        "precipitation": {"GPM_3IMERGM", "IMERG_V07_ATBD"},
        "vegetation_greenness": {"MOD13C2", "MOD13_User_Guide_V61"},
    }
    pairs = [
        ("هل الدلتا بتسخن؟", "Is the Delta warming?"),
        ("رطوبة التربة نسبتها كام؟", "what is the soil moisture?"),
        ("أمطار الصيف", "summer rainfall"),
    ]
    for ar_query, en_query in pairs:
        ar = q(retriever, ar_query)
        en = q(retriever, en_query)
        assert ar["variable_ids"] == en["variable_ids"], (ar_query, en_query)
        assert ar["status"] == en["status"], (ar_query, en_query)
        assert ar["citations"] and en["citations"], (ar_query, en_query)
        for result in (ar, en):
            sources = {c["source_id"] for c in result["citations"]}
            for variable in result["variable_ids"]:
                product_family = {s for s in family[variable]}
                assert sources & product_family, (ar_query, en_query, variable)


def test_product_version_filtering(retriever):
    result = q(retriever, "MERRA-2 temperature data description")
    sources = {c["source_id"] for c in result["citations"]}
    assert all(
        s in ("M2TMNXSLV", "MERRA2_README", "MERRA2_Specification", "MERRA2_Reprocessing")
        for s in sources
    )
    for citation in result["citations"]:
        if citation["product_id"] == "M2TMNXSLV":
            assert citation["product_version"] == "5.12.4"
    product_hit = q(retriever, "M2TMNXSLV collection coverage")
    assert any(c["product_id"] == "M2TMNXSLV" and c["product_version"] == "5.12.4" for c in product_hit["citations"])
    imerg = q(retriever, "IMERG precipitation algorithm")
    imerg_sources = {c["source_id"] for c in imerg["citations"]}
    assert imerg_sources <= {"GPM_3IMERGM", "IMERG_V07_ATBD"}
    assert any(c["product_id"] == "GPM_3IMERGM" and c["product_version"] == "07" for c in imerg["citations"])


def test_definition_and_limitation_context_attached(retriever):
    result = q(retriever, "rainfall trend over the Nile window")
    assert result["variable_ids"] == ["precipitation"]
    assert result["context"]["definition_chunks"], "definition context missing"
    assert all(c["source_kind"] == "product_doc" for c in result["context"]["definition_chunks"])
    assert result["context"]["limitation_chunks"] or result["limitations"]
    assert any("cause" in lim.lower() for lim in result["limitations"])


def test_readiness_integration_region_and_period(retriever):
    result = q(retriever, "temperature", region_id="nile_corridor", period=("2001-01", "2024-12"))
    assert result["status"] == STATUS_RECOMMENDED
    assert result["reason_code"] is None
    entry = result["availability"]["air_temperature"]
    assert entry["measurement_ready"] is True
    assert entry["method_ready"] is True
    assert entry["app_available"] is True
    assert result["suggested_variable_ids"] == ["air_temperature"]


def test_readiness_period_outside_scope(retriever):
    result = q(retriever, "rainfall", region_id="sahel_comparison", period=("1990-01", "1999-12"))
    assert result["status"] == STATUS_UNAVAILABLE
    assert result["reason_code"] == "period_unavailable"
    assert result["suggested_variable_ids"] == []


def test_no_region_never_promises_coverage(retriever):
    result = q(retriever, "اتجاه رطوبة التربة")
    assert result["status"] == STATUS_DOCUMENTED_ONLY
    assert result["reason_code"] == "no_region_selected"
    assert "no executable coverage is promised" in result["availability"]["soil_moisture"]["note"]


def test_cairo_csv_isolation(retriever):
    for query in ["Cairo temperature", "حرارة القاهرة", "temperature trend"]:
        result = q(retriever, query)
        source_ids = {c["source_id"] for c in result["citations"]}
        assert "POWER_Cairo_monthly" not in source_ids
        for citation in result["citations"]:
            assert citation["source_kind"] != "point_sample_celsius_not_regional_cube"
    index_sources = {r.source_id for r in retriever.index.list_sources()}
    assert "POWER_Cairo_monthly" in index_sources
    assert retriever.index.get_source("POWER_Cairo_monthly").segregated is True


def test_alias_provenance_team_authored():
    from packages.rag.aliases import TEAM_AUTHORED_NOTE, ALIAS_PROVENANCE, VARIABLE_ALIASES

    assert set(ALIAS_PROVENANCE) == set(VARIABLE_ALIASES)
    assert "not" in TEAM_AUTHORED_NOTE.lower() and "team" in TEAM_AUTHORED_NOTE.lower()
    for variable, prov in ALIAS_PROVENANCE.items():
        assert prov["product"] and prov["product_version"]
        assert prov["official_source_ids"]


def test_retrieval_never_mutates_display_text(retriever):
    query = "هل الدلتا بِتَّسْخَن؟"
    result = q(retriever, query)
    assert result["query"] == query
    for citation in result["citations"]:
        assert citation["text"]


EVAL_EXPECTATIONS = {
    "هل الدلتا بتسخن؟": {
        "variable_ids": ["air_temperature"],
        "status": STATUS_DOCUMENTED_ONLY,
        "air_vs_surface_note": True,
    },
    "رطوبة التربة نسبتها كام؟": {
        "variable_ids": ["soil_moisture"],
        "status": STATUS_DOCUMENTED_ONLY,
        "units_note": True,
    },
    "ليه الحرارة زادت؟": {
        "variable_ids": ["air_temperature"],
        "status": STATUS_DOCUMENTED_ONLY,
        "causality_guard": True,
    },
    "هل MERRA-2 قياسات محطة؟": {
        "variable_ids": ["air_temperature"],
        "status": STATUS_DOCUMENTED_ONLY,
        "citations_not_empty": True,
    },
    "هل GLDAS قياس مباشر؟": {
        "variable_ids": ["soil_moisture"],
        "status": STATUS_DOCUMENTED_ONLY,
        "citations_not_empty": True,
    },
    "الدلالة 0.03 معناها الاستنتاج صح بنسبة 97%؟": {
        "no_variable_claim": True,
        "no_97_percent_claim": True,
    },
    "هات اتجاه حي مدينة نصر": {
        "status": STATUS_UNSUPPORTED,
        "reason_code": "unsupported_resolution",
    },
    "احسب الاتجاه من 1990": {
        "status": STATUS_UNAVAILABLE,
        "reason_code": "period_outside_scope",
    },
    "هل رطوبة التربة متاحة دلوقتي؟": {
        "variable_ids": ["soil_moisture"],
        "status": STATUS_DOCUMENTED_ONLY,
    },
    "اختيار فترة قصيرة يغيّر الاتجاه؟": {
        "no_numeric_sensitivity_claim": True,
    },
    "هل أقدر أقارن خليتين من شبكتين مختلفتين مباشرة؟": {
        "status": STATUS_UNSUPPORTED,
        "reason_code": "cross_grid_comparison_requires_aggregation",
    },
    "اعمل خريطة دلالة لكل الخلايا": {
        "status": STATUS_UNSUPPORTED,
        "reason_code": "cross_grid_comparison_requires_aggregation",
    },
}


def test_evaluation_questions():
    questions = json.loads(EVAL_PATH.read_text(encoding="utf-8"))
    assert len(questions) == len(EVAL_EXPECTATIONS)
    retriever = Retriever()
    for item in questions:
        question = item["question"]
        assert question in EVAL_EXPECTATIONS, f"no expectation defined for {question!r}"
        expected = EVAL_EXPECTATIONS[question]
        result = retriever.answer_query(question)
        if "variable_ids" in expected:
            assert result["variable_ids"] == expected["variable_ids"], question
        if "status" in expected:
            assert result["status"] == expected["status"], (question, result["status"], result.get("reason_code"))
        if "reason_code" in expected:
            assert result["reason_code"] == expected["reason_code"], question
        if expected.get("air_vs_surface_note"):
            assert any(n["kind"] == "clarification" for n in result["notes"]), question
        if expected.get("units_note"):
            assert any(n["kind"] == "units_check" for n in result["notes"]), question
        if expected.get("causality_guard"):
            assert any(n["kind"] == "causality_guard" for n in result["notes"]), question
        if expected.get("citations_not_empty"):
            assert result["citations"], question
            assert all(c["source_id"] for c in result["citations"])
        if expected.get("no_variable_claim"):
            assert result["variable_ids"] == [], question
            assert result["suggested_variable_ids"] == [], question
        if expected.get("no_97_percent_claim"):
            assert "97" not in json.dumps(result.get("message", "")), question
        if expected.get("no_numeric_sensitivity_claim"):
            assert result["suggested_variable_ids"] == [] or result["status"] in (
                STATUS_UNSUPPORTED,
                STATUS_AMBIGUOUS,
            ), question
            assert not any(
                ch.isdigit() for lim in result["limitations"] if lim != result["limitations"][0]
            ), question


def test_no_network_calls_during_retrieval(retriever, monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket, "socket", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    result = retriever.answer_query("أمطار الدلتا", region_id="nile_corridor", period=("2001-01", "2024-12"))
    assert result["mode"] == "local_retrieval"
    assert result["citations"]


def test_cli_wrapper_offline():
    script = ROOT / "data/nasa/rag/retrieve.py"
    proc = subprocess.run(
        [sys.executable, str(script), "هل الدلتا بتسخن؟"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        cwd=str(ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["mode"] == "local_retrieval_not_generated_answer"
    assert payload["variable_ids"] == ["air_temperature"]

import pytest

from packages.rag.id_mapping import IDMapper, ReadinessLookup


@pytest.fixture(scope="module")
def mapper():
    return IDMapper()


@pytest.fixture(scope="module")
def lookup():
    return ReadinessLookup()


def test_semantic_ids_are_architecture_canonical(mapper):
    assert mapper.semantic_ids() == [
        "air_temperature",
        "precipitation",
        "soil_moisture",
        "vegetation_greenness",
    ]


def test_legacy_dataset_ids_resolve(mapper):
    assert mapper.resolve("T2M") == "air_temperature"
    assert mapper.resolve("SoilMoi0_10cm_inst") == "soil_moisture"
    assert mapper.resolve("GPM_3IMERGM") == "precipitation"
    assert mapper.resolve("MOD13C2") == "vegetation_greenness"
    assert mapper.resolve("M2TMNXSLV") == "air_temperature"
    assert mapper.resolve("GLDAS_NOAH025_M") == "soil_moisture"
    assert mapper.resolve("ndvi") == "vegetation_greenness"
    assert mapper.resolve("NDVI") == "vegetation_greenness"


def test_source_variables_resolve(mapper):
    assert mapper.resolve("CMG_0_05_Deg_Monthly_NDVI") == "vegetation_greenness"
    assert mapper.resolve("precipitation") == "precipitation"
    assert mapper.resolve("T2M") == "air_temperature"


def test_semantic_ids_pass_through(mapper):
    assert mapper.resolve("vegetation_greenness") == "vegetation_greenness"
    assert mapper.resolve("air_temperature") == "air_temperature"


def test_unknown_ids_rejected_no_invented_aliases(mapper):
    with pytest.raises(KeyError):
        mapper.resolve("temperature")
    with pytest.raises(KeyError):
        mapper.resolve("moisture")
    with pytest.raises(KeyError):
        mapper.resolve("NDVIx")
    with pytest.raises(KeyError):
        mapper.resolve("rain")
    with pytest.raises(KeyError):
        mapper.resolve("crop yield")


def test_ndvi_and_mod13c2_aliases_resolve_case_insensitive(mapper):
    assert mapper.resolve("ndvi") == "vegetation_greenness"
    assert mapper.resolve("NDVI") == "vegetation_greenness"
    assert mapper.resolve("NdVi") == "vegetation_greenness"
    assert mapper.resolve("MOD13C2") == "vegetation_greenness"
    assert mapper.resolve("mod13c2") == "vegetation_greenness"
    assert mapper.resolve(" MOD13C2 ") == "vegetation_greenness"
    assert mapper.resolve("t2m") == "air_temperature"


def test_mapping_derived_from_scope_not_hardcoded_text(mapper):
    scope_sources = {(e["product_id"], e["source_variable"]) for e in mapper.scope["entries"]}
    for product, source_variable in scope_sources:
        assert mapper.by_product_variable[(product, source_variable)] in mapper.semantic_ids()


def test_full_readiness_grid_twelve_entries(lookup):
    assert len(lookup.entries) == 12
    assert set(lookup.region_ids()) == {"nile_corridor", "morocco_comparison", "sahel_comparison"}


def test_readiness_flags_from_registry(lookup):
    result = lookup.lookup("air_temperature", "nile_corridor", ("2001-01", "2024-12"))
    assert result["found"] is True
    assert result["measurement_ready"] is True
    assert result["method_ready"] is True
    assert result["app_available"] is True
    assert result["product_id"] == "M2TMNXSLV"
    assert result["product_version"] == "5.12.4"


def test_readiness_resolves_aliases_and_legacy_ids(lookup):
    result_alias = lookup.lookup("ndvi", "nile_corridor")
    assert result_alias["found"] is True
    assert result_alias["variable_id"] == "vegetation_greenness"
    assert result_alias["product_id"] == "MOD13C2"

    result_legacy = lookup.lookup("T2M", "morocco_comparison")
    assert result_legacy["found"] is True
    assert result_legacy["variable_id"] == "air_temperature"
    assert result_legacy["product_id"] == "M2TMNXSLV"


def test_all_pairs_are_ready_for_analysis(lookup):
    for entry in lookup.entries:
        assert entry["measurement_ready"] is True
        assert entry["method_ready"] is True
        assert entry["app_available"] is True


def test_unknown_pair_reports_reason_not_exception(lookup):
    result = lookup.lookup("air_temperature", "atlantis", ("2001-01", "2024-12"))
    assert result["found"] is False
    assert result["reason_code"] == "unknown_variable_or_region"


def test_period_outside_window_unavailable(lookup):
    result = lookup.lookup("soil_moisture", "sahel_comparison", ("1990-01", "1999-12"))
    assert result["found"] is True
    assert result["measurement_ready"] is False
    assert result["reason_code"] == "period_unavailable"
    assert "1990-01" in result["period_note"]


def test_partial_period_overlap_unavailable(lookup):
    result = lookup.lookup("soil_moisture", "sahel_comparison", ("2005-01", "2030-12"))
    assert result["reason_code"] == "period_unavailable"


def test_data_revision_recorded_and_mismatch_flagged(lookup):
    assert lookup.data_revision == "2026-11-14"
    result = lookup.lookup("air_temperature", "nile_corridor", ("2001-01", "2024-12"), data_revision="v1")
    assert result["reason_code"] == "data_revision_mismatch"
    result_ok = lookup.lookup("air_temperature", "nile_corridor", ("2001-01", "2024-12"), data_revision="2026-11-14")
    assert result_ok["reason_code"] is None


def test_available_for_period_respects_window(lookup):
    available = lookup.available_for_period(("2001-01", "2024-12"))
    assert len(available) == 12
    assert lookup.available_for_period(("1990-01", "1994-12")) == []


def test_app_availability_is_read_from_the_runtime_registry(lookup, mapper):
    result = lookup.lookup("precipitation", "morocco_comparison")
    assert result["app_available"] is True
    assert result["reason_code"] is None

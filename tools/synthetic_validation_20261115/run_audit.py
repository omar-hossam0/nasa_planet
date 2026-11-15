"""Isolated, retained synthetic audit. Never imported by the application.

Run from repository root: python tools/synthetic_validation_20261115/run_audit.py
No network/provider calls, source changes, inference release, or automatic deletion.
"""
from pathlib import Path
import calendar
import hashlib
import json
import sys
import time
from types import SimpleNamespace as NS
from unittest.mock import patch

import numpy as np
import xarray as xr

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]
OUT = Path(__file__).resolve().parent
from packages.science.src.trend_estimation import trend_series, sen_slopes
from packages.science.src.preparation import prepare_series
from packages.science.src.preprocessing import load_policy
from packages.science.src.data_loader import input_entry
from packages.science.src.regional_series import BoundingBox
from packages.science.src.inference import annual_inference, wilson_interval
from packages.science.src.inference_candidates import adjusted_mk, ar1_regression
from packages.rag.retriever import Retriever, BM25
from packages.rag.provider import GeminiClient
from packages.rag.facade import Role04Service
from app.adapters.science_rag import ScienceRAGAdapter
from app.schemas.common import Language


def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def main():
    started = time.perf_counter()
    protocol = {"seed": 20261115, "years": 24, "records_per_scenario": 300,
                "rho": [0., .7, .9], "true_slopes": [0., .08],
                "noise": "stationary Gaussian AR(1), marginal SD=1, known generating slope",
                "bootstrap_replicates": 199, "block_length": 4, "confidence": .95,
                "scope": "current descriptive code, experimental inference candidates, offline retrieval and templates",
                "not_tested": "live Gemini answer quality, browser, deployment, exhaustive inference calibration",
                "retention": "Keep fixtures, outputs and code until user explicitly requests deletion",
                "production_changes": False}
    save("protocol.json", protocol)  # Fixed before any outcomes are inspected.
    checks, fixtures, template_outputs, rag_outputs = [], [], [], []

    def check(name, action):
        try:
            detail = action()
            checks.append({"name": name, "passed": True, "detail": detail})
        except Exception as exc:
            checks.append({"name": name, "passed": False, "error": f"{type(exc).__name__}: {exc}"})

    def equal(actual, expected, tolerance=1e-9):
        assert np.allclose(actual, expected, atol=tolerance, rtol=0, equal_nan=True), (actual, expected)

    years = np.arange(2001, 2025)
    t = years - years[0]
    for label, slope in [("warming", .03125), ("cooling", -.125), ("flat", 0.)]:
        y = 290. + slope * t
        fixtures.append({"name": label, "years": years.tolist(), "values": y.tolist(), "expected_slope": slope})
        def exact(y=y, slope=slope):
            result = trend_series(y, t)
            equal(result["slope_per_year"], slope)
            assert result["inference_status"] == "not_computed"
            return result
        check("science/" + label, exact)

    def gap_check():
        axis = np.array([2001, 2002, 2007, 2013, 2024])
        values = 280 + .2 * (axis - 2001)
        values[2] = np.nan
        result = trend_series(values, axis)
        equal(result["slope_per_year"], .2)
        assert result["n_valid"] == 4 and result["valid_span_years"] == 23
        return result
    check("science/missing_values_and_elapsed_year_gaps", gap_check)

    def outlier_check():
        y = 290 + .03125 * t
        y[12] += 1000
        equal(trend_series(y, t)["slope_per_year"], .03125)
    check("science/single_extreme_outlier", outlier_check)
    check("science/grid_positive_negative_zero", lambda: equal(sen_slopes(
        np.stack([t * .1, t * -.2, t * 0], axis=1), t)["slope"], [.1, -.2, 0]))

    def rejected_time():
        try:
            trend_series([1., 2., 3.], [0, 0, 1])
        except ValueError:
            return "duplicate timestamps rejected"
        raise AssertionError("duplicate timestamps accepted")
    check("science/duplicate_years_rejected", rejected_time)
    check("science/too_few_values", lambda: equal(
        int(trend_series([1., np.nan, 2.], [0, 1, 2])["slope_per_year"] is None), 1))

    # Actual preparation -> QA -> annual aggregation -> slope -> backend templates.
    # Each NetCDF has 288 months, 4 native cells and explicitly synthetic provenance.
    specs = [("air_temperature", "K", 290., .03125),
             ("soil_moisture", "kg m-2", 20., -.125),
             ("vegetation_greenness", "1", .3, .001),
             ("precipitation", "mm/hr", 100., 2.)]
    retained = {}
    for variable, unit, base, slope in specs:
        entry = input_entry(variable, "nile_corridor")
        west, south, east, north = entry["bbox"]
        dy, dx = load_policy()["spatial"]["native_spacing_degrees"][entry["product_id"]]
        coords = {"time": np.arange("2001-01", "2025-01", dtype="datetime64[M]"),
                  "lat": [south + dy, south + 2*dy],
                  "lon": [west + dx, west + 2*dx]}
        annual_truth = base + slope * t
        monthly = np.repeat(annual_truth, 12)
        if variable == "precipitation":
            hours = np.array([calendar.monthrange(int(str(d)[:4]), int(str(d)[5:7]))[1] * 24 for d in coords["time"]])
            monthly = monthly / 12 / hours  # annual total known exactly, leap years included
        cube = xr.Dataset({entry["cube_variable"]: (("time", "lat", "lon"), np.broadcast_to(monthly[:, None, None], (288, 2, 2)).copy())}, coords=coords,
                          attrs={"product": entry["product_id"], "synthetic": "TEST ONLY; not NASA observations"})
        cube[entry["cube_variable"]].attrs["units"] = unit
        if variable == "vegetation_greenness":
            for field in ("VI_Quality", "pixel_reliability"):
                cube[field] = xr.zeros_like(cube[entry["cube_variable"]], dtype=int)
        if variable == "precipitation":
            cube["precipitationQualityIndex"] = xr.ones_like(cube[entry["cube_variable"]])
            cube["randomError"] = xr.zeros_like(cube[entry["cube_variable"]])
        cube.to_netcdf(OUT / (variable + "_SYNTHETIC.nc"))
        def pipeline(cube=cube, entry=entry, variable=variable, slope=slope, annual_truth=annual_truth):
            original = cube.copy(deep=True)
            prepared, metadata = prepare_series(cube, entry)
            xr.testing.assert_identical(cube, original)
            equal(prepared.regional_annual.values, annual_truth)
            equal(prepared.cell_annual.values, np.broadcast_to(annual_truth[:, None, None], (24, 2, 2)))
            result = trend_series(prepared.regional_annual.values, prepared.year.values)
            equal(result["slope_per_year"], slope)
            assert metadata["eligible_fixed_support_cells"] == 4
            retained[variable] = (cube, entry, prepared, metadata, result)
            return {"expected": slope, "actual": result["slope_per_year"], "unit": prepared.regional_annual.attrs["units"]}
        check("pipeline/" + variable, pipeline)

    def qa_check():
        cube, entry, *_ = retained["vegetation_greenness"]
        bad = cube.copy(deep=True)
        bad.pixel_reliability.values[0, 0, 0] = 3
        prepared, metadata = prepare_series(bad, entry)
        assert metadata["eligible_fixed_support_cells"] == 3
        assert np.isnan(prepared.cell_monthly.values[:, 0, 0]).all()
        equal(trend_series(prepared.regional_annual.values, prepared.year.values)["slope_per_year"], .001)
        return {"expected_retained_cells": 3, "actual": metadata["eligible_fixed_support_cells"]}
    check("pipeline/one_bad_QA_month_excludes_cell_for_full_reference", qa_check)

    def bbox_check():
        cube, entry, *_ = retained["air_temperature"]
        try:
            prepare_series(cube, entry, bbox=BoundingBox(-170, -80, -160, -70))
        except ValueError:
            return "outside region rejected"
        raise AssertionError("outside region accepted")
    check("pipeline/unsupported_AOI_rejected", bbox_check)

    def spatial_weight_check():
        cube, entry, *_ = retained["air_temperature"]
        varied = cube.copy(deep=True)
        slopes = np.array([[.1, -.2], [.3, .4]])
        varied[entry["cube_variable"]].values[:] = 290 + np.repeat(t, 12)[:, None, None]*slopes
        prepared, _ = prepare_series(varied, entry)
        # Independent spherical-area oracle: row area proportional to cos(latitude).
        weights = np.broadcast_to(np.cos(np.deg2rad(varied.lat.values))[:, None], (2, 2))
        expected = float(np.sum(weights*slopes)/weights.sum())
        observed = trend_series(prepared.regional_annual.values, prepared.year.values)["slope_per_year"]
        equal(observed, expected)
        return {"independent_area_weighted_slope": expected, "actual": observed}
    check("pipeline/nonuniform_cells_independent_area_weight_oracle", spatial_weight_check)

    retriever = Retriever()
    corpus = {c["chunk_id"]: c for c in retriever.chunks}
    questions = [
        ("What does MERRA-2 air temperature measure?", "air_temperature"),
        ("ما قيود قياس درجة حرارة الهواء؟", "air_temperature"),
        ("هل دلتا النيل بتسخن؟", "air_temperature"),
        ("الدنيا بتسخن في الدلتا؟", "air_temperature"),
        ("Is the Nile Delta getting warmer?", "air_temperature"),
        ("What does GLDAS soil moisture measure?", "soil_moisture"),
        ("ما حدود بيانات رطوبة التربة؟", "soil_moisture"),
        ("What are IMERG precipitation limitations?", "precipitation"),
        ("ما قيود قياس الهطول؟", "precipitation"),
        ("What does NDVI measure?", "vegetation_greenness"),
        ("ما معنى مؤشر NDVI؟", "vegetation_greenness"),
    ]
    for query, expected in questions:
        def retrieval(query=query, expected=expected):
            answer = retriever.answer_query(query)
            rag_outputs.append(answer)
            assert expected in answer["variable_ids"], answer
            assert answer["citations"], answer
            for citation in answer["citations"]:
                original = corpus[citation["chunk_id"]]
                assert citation["text"] == original["text"]
                assert citation["source_url"] == original["source_url"]
            return {"variable_ids": answer["variable_ids"], "citation_count": len(answer["citations"])}
        check("rag/question/" + query, retrieval)
    for query in ["atmospheric humidity", "earthquake prediction", "temperature in 1990", "رطوبة"]:
        def unsupported(query=query):
            answer = retriever.answer_query(query)
            rag_outputs.append(answer)
            assert answer["status"] in ("unsupported", "ambiguous", "unavailable"), answer
            return {"status": answer["status"], "reason": answer.get("reason_code")}
        check("rag/safety/" + query, unsupported)
    def tiny_corpus():
        documents = [["rain", "precipitation", "mm"], ["temperature", "air", "kelvin"], ["soil", "moisture"]]
        index = BM25(documents)
        assert max(range(3), key=lambda i: index.score(["temperature"], i)) == 1
        assert max(range(3), key=lambda i: index.score(["rain"], i)) == 0
        save("synthetic_retrieval_corpus.json", documents)
    check("rag/isolated_synthetic_corpus_ranking", tiny_corpus)

    def unsupported_region():
        answer = retriever.answer_query("air temperature", region_id="sinai")
        rag_outputs.append(answer)
        assert answer["status"] in ("unavailable", "unsupported", "documented_only"), answer
        assert answer["status"] != "recommended"
        return {"status": answer["status"], "reason": answer.get("reason_code")}
    check("rag/Sinai_does_not_become_executable_region", unsupported_region)

    adapter = ScienceRAGAdapter()
    for variable, (_, entry, prepared, metadata, result) in retained.items():
        mock_result = NS(result_id="SYNTHETIC_" + variable, job_id="SYNTHETIC_job",
            receipt_id="SYNTHETIC_receipt", analysis=NS(region_id="nile_corridor", region_display_name="SYNTHETIC study area", start_month="2001-01", end_month="2024-12"),
            variables=[NS(variable_id=variable, unit=prepared.regional_monthly.attrs["units"],
                series=[NS(value=float(v)) for v in prepared.regional_monthly.values],
                trend=NS(slope_per_year=result["slope_per_year"], slope_unit=prepared.regional_annual.attrs["units"] + " per year", n_years=24))],
            datasets=[NS(variable_id=variable, product_id=entry["product_id"], version=entry["version"])],
            science={variable: {"metadata": metadata, "positive_cells": int(result["slope_per_year"] > 0)*4, "negative_cells": int(result["slope_per_year"] < 0)*4}})
        for language in (Language.en, Language.ar):
            def template(mock_result=mock_result, language=language, variable=variable):
                with patch.object(GeminiClient, "generate", side_effect=AssertionError("LLM forbidden for result templates")):
                    rendered = adapter.explain(mock_result, language)
                assert rendered.mode == "conclusion_templates"
                text = "\n".join(s[2] for s in rendered.sections)
                assert format(mock_result.variables[0].trend.slope_per_year, ".8g") in text
                assert rendered.references
                template_outputs.append({"variable": variable, "language": language.value, "sections": rendered.sections})
                return {"mode": rendered.mode, "slope_preserved": True, "provider_calls": 0}
            check("rag/backend_templates/" + variable + "/" + language.value, template)

    # Independent synthetic records. Generating slopes known, realized estimates random.
    rng = np.random.default_rng(protocol["seed"])
    diagnostics, samples = [], {}
    methods = {"block_bootstrap_candidate": lambda y, seed: annual_inference(y, years, replicates=199, seed=seed),
               "adjusted_MK_candidate": lambda y, seed: adjusted_mk(y, years),
               "AR1_regression_candidate": lambda y, seed: ar1_regression(y, years)}
    for rho in protocol["rho"]:
        for beta in protocol["true_slopes"]:
            errors = np.empty((300, 24))
            errors[:, 0] = rng.normal(size=300)
            for i in range(1, 24):
                errors[:, i] = rho * errors[:, i-1] + np.sqrt(1-rho*rho)*rng.normal(size=300)
            records = 290 + beta*t + errors
            samples[f"rho{rho}_slope{beta}"] = records
            for name, method in methods.items():
                rejected, covered, estimates, failures, nonconverged = 0, 0, [], [], 0
                for i, y in enumerate(records):
                    try:
                        result = method(y, protocol["seed"] + i)
                        p = result.get("p_value_candidate", result.get("p"))
                        interval = result.get("interval_candidate", result.get("interval"))
                        assert p is not None and 0 <= p <= 1 and interval is not None
                        nonconverged += result["status"] == "nonconverged"
                        rejected += p < .05
                        covered += interval[0] <= beta <= interval[1]
                        estimates.append(result.get("slope_per_year", result.get("slope")))
                    except Exception as exc:
                        failures.append({"record": i, "error": str(exc)})
                n = len(estimates)
                diagnostics.append({"method": name, "rho": rho, "true_slope": beta, "records": 300,
                    "valid_outputs": n, "nonconverged": nonconverged, "failures": failures,
                    "rejection_rate": rejected/n if n else None,
                    "rejection_rate_MC95": wilson_interval(rejected, n) if n else None,
                    "coverage": covered/n if n else None,
                    "coverage_MC95": wilson_interval(covered, n) if n else None,
                    "slope_bias": float(np.mean(estimates)-beta) if n else None,
                    "slope_RMSE": float(np.sqrt(np.mean((np.array(estimates)-beta)**2))) if n else None,
                    "production_enabled": False})
    np.savez_compressed(OUT / "synthetic_noise_records.npz", years=years, **samples)

    def confidence_check():
        y = samples["rho0.7_slope0.08"][0]
        a = annual_inference(y, years, replicates=199, seed=42, confidence=.95)
        b = annual_inference(y, years, replicates=199, seed=42, confidence=.90)
        assert a["p_value_candidate"] == b["p_value_candidate"]
        width = lambda x: x["interval_candidate"][1]-x["interval_candidate"][0]
        assert width(b) <= width(a)
        return {"p_95": a["p_value_candidate"], "p_90": b["p_value_candidate"], "width_95": width(a), "width_90": width(b)}
    check("inference/confidence_change_does_not_change_p", confidence_check)
    save("fixtures.json", fixtures)
    save("retrieval_outputs.json", rag_outputs)
    save("template_outputs.json", template_outputs)
    result = {"protocol": protocol, "checks": checks, "passed": sum(c["passed"] for c in checks),
              "failed": sum(not c["passed"] for c in checks), "inference_diagnostics": diagnostics,
              "elapsed_seconds": round(time.perf_counter()-started, 2)}
    save("results.json", result)
    paths = [Path(__file__), *[ROOT / p for p in ["packages/science/src/trend_estimation.py", "packages/science/src/preparation.py", "packages/science/src/inference.py", "packages/science/src/inference_candidates.py", "packages/rag/retriever.py", "packages/rag/conclusions.py", "backend/app/adapters/science_rag.py"]]]
    save("code_hashes.json", {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    print(json.dumps({"passed": result["passed"], "failed": result["failed"], "elapsed_seconds": result["elapsed_seconds"], "failed_checks": [c for c in checks if not c["passed"]]}, ensure_ascii=True))
    return 1 if result["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())

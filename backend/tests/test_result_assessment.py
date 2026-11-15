"""Rule-based claims stay tied to the actual result, never fabricated inference."""
import copy
from types import SimpleNamespace as NS
import numpy as np
import pytest

from app.services.result_assessment import assess_variable, render_assessment, load_assessment_policy
from packages.science.src.trend_estimation import trend_series


def fixture(n=24, y=None, area=1.):
    years = np.arange(2001, 2001+n)
    values = np.array(y, dtype=float) if y is not None else 290-.125*np.arange(n)
    estimate = trend_series(values, years)
    variable = NS(variable_id='air_temperature', unit='K',
        series=[NS(value=float(v)) for v in np.repeat(values, 12)],
        trend=NS(slope_per_year=estimate['slope_per_year'], slope_unit='K year-1',
                 n_years=estimate['n_valid'], n_months=int(np.isfinite(values).sum())*12, p_value=None))
    result = NS(result_id='actual_test_result', analysis=NS(start_month='2001-01', end_month=f'{years[-1]}-12'),
        science={'air_temperature': {'annual_years': years.tolist(), 'regional_annual': values.tolist(),
            'metadata': {'selected_cell_count': 10, 'eligible_fixed_support_cells': 10 if area==1 else 2,
                         'fixed_support_area_fraction_of_selected_native_cells': area}}})
    return result, variable


def codes(a):
    return {r.code for r in a.reasons}


def test_short_negative_window_has_descriptive_direction_not_significance():
    result, variable = fixture(n=5)
    a = assess_variable(result, variable, 'en')
    assert a.descriptive_status == 'available' and a.direction == 'decrease'
    assert a.facts.complete_years == 5 and a.facts.valid_months == 60
    assert a.facts.slope_per_year == -.125
    assert 'short_annual_record' in codes(a)
    assert a.inference_status == 'not_available'
    assert a.diagnostics_status == 'not_run_for_this_result'
    text = ' '.join(s[2] for s in render_assessment(a, 'en'))
    assert '-0.125' in text and '°C/year' in text and '5 complete' in text


def test_long_record_never_implies_approval_and_ignores_stray_p():
    result, variable = fixture()
    variable.trend.p_value = .00001
    result.method = NS(approved=True)
    a = assess_variable(result, variable, 'en')
    assert 'short_annual_record' not in codes(a)
    assert 'unreleased_inference_value_ignored' in codes(a)
    assert a.inference_status == 'not_available'


def test_low_area_and_no_support_have_distinct_meaning():
    result, variable = fixture(area=.147)
    a = assess_variable(result, variable, 'en')
    assert a.descriptive_status == 'available'
    assert 'limited_spatial_support' in codes(a)
    result.science['air_temperature']['metadata'].update(eligible_fixed_support_cells=0,
        fixed_support_area_fraction_of_selected_native_cells=0.)
    a = assess_variable(result, variable, 'en')
    assert a.descriptive_status == 'insufficient_data' and a.direction == 'unavailable'
    assert 'no_qa_support' in codes(a)


def test_leave_one_out_sign_changes_are_not_confidence():
    result, variable = fixture(n=5, y=[0., 1., 0., 1., 0.])
    a = assess_variable(result, variable, 'en')
    assert a.direction == 'no_estimated_change'
    assert 'direction_sensitive_to_one_year' in codes(a)
    assert a.facts.leave_one_year_out_min_slope < 0 < a.facts.leave_one_year_out_max_slope
    assert a.facts.leave_one_year_out_same_sign_count < 5


@pytest.mark.parametrize('corruption', ['slope', 'year_count', 'month_count', 'outside_period', 'missing_artifact'])
def test_mismatched_evidence_blocks_direction(corruption):
    result, variable = fixture()
    if corruption == 'slope': variable.trend.slope_per_year = 123.
    if corruption == 'year_count': variable.trend.n_years = 2
    if corruption == 'month_count': variable.trend.n_months = 1
    if corruption == 'outside_period': result.analysis.end_month = '2005-12'
    if corruption == 'missing_artifact': del result.science['air_temperature']['regional_annual']
    a = assess_variable(result, variable, 'en')
    assert a.descriptive_status == 'inconsistent_result'
    assert a.direction == 'unavailable'


def test_arabic_english_same_facts_and_reasons_no_mutation():
    result, variable = fixture(n=5, area=.2)
    before = copy.deepcopy(result)
    en = assess_variable(result, variable, 'en')
    ar = assess_variable(result, variable, 'ar')
    assert en.facts == ar.facts and codes(en) == codes(ar)
    assert 'انخفاض' in ar.headline
    assert 'الفترة فيها 5' in next(r.message for r in ar.reasons if r.code=='short_annual_record')
    assert result.science == before.science
    assert en.facts.mean_celsius == pytest.approx(en.facts.mean_monthly_value-273.15)
    assert ar.model_dump_json()


def test_missing_annual_values_not_imputed_or_time_compressed():
    result, variable = fixture(n=6, y=[290., np.nan, 289.75, 289.625, 289.5, 289.375])
    a = assess_variable(result, variable, 'en')
    assert a.descriptive_status == 'available'
    assert a.facts.complete_years == 5 and a.facts.slope_per_year == -.125
    assert 'incomplete_annual_years' in codes(a)


def test_configurable_review_thresholds_do_not_change_evidence():
    result, variable = fixture(n=5, area=.2)
    policy = load_assessment_policy().model_copy(update={'short_record_review_years': 4,
                                                      'spatial_support_review_fraction': .1})
    a = assess_variable(result, variable, 'en', policy)
    assert 'short_annual_record' not in codes(a) and 'limited_spatial_support' not in codes(a)
    assert a.inference_status == 'not_available' and a.facts.slope_per_year == -.125

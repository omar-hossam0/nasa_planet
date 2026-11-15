"""Assess actual request artifacts; no LLM or saved full-period audit is consulted.

This policy explains descriptive results and their restrictions. It cannot approve
an inferential model, promote a diagnostic p-value, or certify significance.
"""
from functools import lru_cache
import json
import math
from pathlib import Path

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.assessment import AssessmentFacts, AssessmentReason, ResultAssessment
from packages.science.src.trend_estimation import trend_series
from packages.rag.judge import InferenceEvidence, judge_inference


class AssessmentPolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid')
    revision: str
    minimum_descriptive_years: int = Field(ge=3)
    short_record_review_years: int = Field(ge=3)
    spatial_support_review_fraction: float = Field(ge=0, le=1)
    note: str

    @model_validator(mode='after')
    def ordered_thresholds(self):
        if self.short_record_review_years < self.minimum_descriptive_years:
            raise ValueError('Review threshold cannot be below the descriptive minimum')
        return self


@lru_cache(maxsize=1)
def load_assessment_policy():
    path = Path(__file__).resolve().parents[2]/'config/assessment_policy.json'
    return AssessmentPolicy.model_validate(json.loads(path.read_text(encoding='utf-8')))


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def assess_variable(result, variable, language, policy=None):
    policy = policy or load_assessment_policy()
    ar = getattr(language, 'value', language) == 'ar'
    artifact = (result.science or {}).get(variable.variable_id, {})
    metadata = artifact.get('metadata', {})
    values = [p.value for p in variable.series if finite(p.value)]
    mean = math.fsum(values)/len(values) if values else None
    slope = variable.trend.slope_per_year
    facts = AssessmentFacts(slope_per_year=float(slope) if finite(slope) else None,
        slope_unit=variable.trend.slope_unit, monthly_unit=variable.unit,
        mean_monthly_value=mean, valid_months=len(values),
        complete_years=variable.trend.n_years,
        mean_celsius=mean-273.15 if mean is not None and variable.variable_id=='air_temperature' and variable.unit=='K' else None)
    reasons = []
    def reason(code, severity, en, arabic):
        reasons.append(AssessmentReason(code=code, severity=severity, message=arabic if ar else en))

    reason('inference_not_released', 'blocking',
        'No inference method is released for this result. A descriptive slope does not establish statistical significance.',
        'لا توجد طريقة استدلال مُعتمدة لهذه النتيجة حاليًا. الميل الوصفي وحده لا يثبت الدلالة الإحصائية.')
    # An approved flag or a stray p-value alone is never sufficient authorization.
    if variable.trend.p_value is not None:
        reason('unreleased_inference_value_ignored', 'blocking',
            'An unreleased inferential value was supplied; it is not used to claim significance.',
            'وردت قيمة استدلال غير مُعتمدة؛ لم تُستخدم لإعلان الدلالة الإحصائية.')

    status = 'available'
    if len(values) != variable.trend.n_months:
        status = 'inconsistent_result'
        reason('monthly_count_inconsistent', 'blocking',
            'The stored valid-month count differs from the displayed monthly values.',
            'عدد الشهور الصالحة المحفوظ لا يطابق القيم الشهرية المعروضة.')
    annual_values = artifact.get('regional_annual')
    annual_years = artifact.get('annual_years')
    annual_pairs = None
    try:
        if annual_values is None or annual_years is None or len(annual_values) != len(annual_years):
            raise ValueError('missing aligned annual artifact')
        axis = np.asarray(annual_years, dtype=float)
        raw = np.array([np.nan if v is None else v for v in annual_values], dtype=float)
        if not np.isfinite(axis).all() or not np.all(np.diff(axis)>0) or np.isinf(raw).any():
            raise ValueError('invalid annual artifact')
        first, last = int(result.analysis.start_month[:4]), int(result.analysis.end_month[:4])
        if np.any(axis != np.floor(axis)) or np.any(axis < first) or np.any(axis > last):
            raise ValueError('annual artifact outside requested years')
        valid = np.isfinite(raw)
        annual_pairs = (axis[valid], raw[valid])
        if int(valid.sum()) != variable.trend.n_years:
            raise ValueError('stored count differs from actual annual values')
        if int(valid.sum()) < len(raw):
            reason('incomplete_annual_years', 'warning',
                f'Only {int(valid.sum())} of {len(raw)} calendar years have complete annual values. Partial or missing years were not filled.',
                f'توجد قيم سنوية مكتملة لـ{int(valid.sum())} من {len(raw)} سنة تقويمية. لم تُستكمل السنوات الجزئية أو الناقصة بقيم مصطنعة.')
        if valid.sum() >= policy.minimum_descriptive_years and finite(slope):
            checked = trend_series(raw, axis, min_points=policy.minimum_descriptive_years)['slope_per_year']
            if not math.isclose(checked, slope, rel_tol=1e-8, abs_tol=1e-12):
                raise ValueError('stored slope differs from annual values')
    except (TypeError, ValueError, OverflowError):
        status = 'inconsistent_result'
        reason('annual_evidence_inconsistent', 'blocking',
            'The stored annual values, years or slope could not be reconciled. Re-run analysis before interpreting this result.',
            'تعذر التحقق من تطابق القيم السنوية والسنوات والميل المحفوظ. أعد التحليل قبل تفسير النتيجة.')

    if status != 'inconsistent_result' and (not values or not finite(slope) or facts.complete_years < policy.minimum_descriptive_years):
        status = 'insufficient_data'
        reason('insufficient_descriptive_data', 'blocking',
            f'At least {policy.minimum_descriptive_years} complete annual observations and a finite slope are required for this descriptive estimate.',
            f'هذا التقدير الوصفي يتطلب {policy.minimum_descriptive_years} قيم سنوية مكتملة على الأقل وميلًا قابلًا للحساب.')
    if facts.complete_years < policy.short_record_review_years:
        reason('short_annual_record', 'warning',
            f'Only {facts.complete_years} complete annual observations are available. Current inference studies start at {policy.short_record_review_years} years; reaching that count does not validate a test.',
            f'الفترة فيها {facts.complete_years} قيم سنوية مكتملة فقط. دراسات الاستدلال الحالية تبدأ من {policy.short_record_review_years} سنة؛ والوصول لهذا العدد لا يضمن صلاحية الاختبار.')

    selected, retained, area = (metadata.get(k) for k in ('selected_cell_count', 'eligible_fixed_support_cells', 'fixed_support_area_fraction_of_selected_native_cells'))
    if (isinstance(selected, int) and not isinstance(selected, bool) and selected > 0
            and isinstance(retained, int) and not isinstance(retained, bool) and 0 <= retained <= selected
            and finite(area) and 0 <= area <= 1 and ((retained == 0) == (area == 0))):
        facts.selected_cells, facts.retained_cells, facts.retained_area_fraction = selected, retained, area
        if retained == 0:
            status = 'insufficient_data' if status != 'inconsistent_result' else status
            reason('no_qa_support', 'blocking', 'No QA-valid fixed-support cells are available.',
                   'لا توجد خلايا مقبولة بالجودة ضمن الدعم المكاني الثابت.')
        if area < policy.spatial_support_review_fraction:
            reason('limited_spatial_support', 'warning',
                f'QA retained {area*100:.1f}% of selected native-cell area. Results describe retained cells and may not represent the whole selected rectangle. This is a review warning, not a NASA rejection threshold.',
                f'احتفظ فحص الجودة بـ{area*100:.1f}% من مساحة الخلايا المختارة. النتيجة تخص الخلايا المحتفظ بها وقد لا تمثل المستطيل كله. هذا تنبيه للمراجعة وليس حد رفض صادرًا من ناسا.')
    else:
        reason('spatial_support_unverified', 'warning',
            'Spatial support metadata is missing or inconsistent; regional representativeness cannot be assessed.',
            'بيانات التغطية المكانية ناقصة أو غير متطابقة؛ لا يمكن تقييم تمثيل النتيجة للمنطقة.')

    if status == 'available' and annual_pairs is not None and len(annual_pairs[0]) >= 4:
        years, annual = annual_pairs
        slopes = [trend_series(np.delete(annual, i), np.delete(years, i))['slope_per_year'] for i in range(len(years))]
        facts.leave_one_year_out_min_slope = min(slopes)
        facts.leave_one_year_out_max_slope = max(slopes)
        facts.leave_one_year_out_windows = len(slopes)
        facts.leave_one_year_out_same_sign_count = int(sum(np.sign(s)==np.sign(slope) for s in slopes))
        if facts.leave_one_year_out_same_sign_count < len(slopes):
            reason('direction_sensitive_to_one_year', 'warning',
                'Removing individual years changes the sign of the estimated slope in some checks. This sensitivity check is not a confidence interval or significance test.',
                'حذف سنة واحدة يغيّر إشارة الميل في بعض التجارب. هذا فحص حساسية، وليس فترة ثقة أو اختبار دلالة.')
    reason('request_model_diagnostics_not_run', 'info',
        'Statistical model diagnostics have not been run for this exact area and period. An audit of a different selection is not an approval of this result.',
        'لم تُجرَ فحوص ملاءمة النموذج لهذه المساحة والفترة تحديدًا. تقرير فحص لاختيار مختلف لا يُعد اعتمادًا لهذه النتيجة.')
    direction = ('increase' if slope > 0 else 'decrease' if slope < 0 else 'no_estimated_change') if status=='available' else 'unavailable'
    headlines = {
        'increase': ('Descriptive increase; statistical significance unavailable', 'زيادة وصفية خلال الفترة؛ الدلالة الإحصائية غير متاحة'),
        'decrease': ('Descriptive decrease; statistical significance unavailable', 'انخفاض وصفي خلال الفترة؛ الدلالة الإحصائية غير متاحة'),
        'no_estimated_change': ('Zero descriptive slope; this does not prove stability', 'الميل الوصفي يساوي صفرًا؛ هذا لا يثبت الاستقرار'),
        'unavailable': ('Result needs review before interpretation', 'النتيجة تحتاج مراجعة قبل تفسيرها')}
    source = next((d for d in getattr(result, 'datasets', []) if d.variable_id == variable.variable_id), None)
    inference = getattr(variable.trend, 'inference', None) or InferenceEvidence(status='not_computed', reason_code='inference_not_released')
    return ResultAssessment(policy_revision=policy.revision, result_id=result.result_id,
        region_id=getattr(result.analysis, 'region_id', None), start_month=result.analysis.start_month,
        end_month=result.analysis.end_month, source_product_id=getattr(source, 'product_id', None),
        source_product_version=getattr(source, 'version', None),
        variable_id=variable.variable_id, descriptive_status=status, direction=direction,
        headline=headlines[direction][1 if ar else 0], reasons=reasons, facts=facts,
        inference=inference,
        judgment=judge_inference(inference, 'ar' if ar else 'en'))


from packages.rag.result_templates import render_assessment  # compatibility export

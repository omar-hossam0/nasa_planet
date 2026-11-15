LANGUAGE_EN = "en"
LANGUAGE_AR = "ar"
LANGUAGES = (LANGUAGE_EN, LANGUAGE_AR)

MODE = "conclusion_templates"

PERMITTED_ACTIONS = {
    "FOCUS_REGION",
    "FOCUS_REGIONAL_CHART",
    "REVEAL_CELLS",
    "OPEN_SPIN_IT",
    "OPEN_RECEIPT",
}
COMPARISON_ACTIONS = set()

CANONICAL_VARIABLE_IDS = ("air_temperature", "soil_moisture", "precipitation", "vegetation_greenness")

REQUIRED_FIELDS = ("analysis_id", "request_id", "region_id", "variable_id", "period", "units", "product", "regional")

RESULT_STATES = ("succeeded", "insufficient_data", "failed")

DENOMINATORS = ("eligible_cells", "weighted_area")

VARIABLE_LABELS = {
    "air_temperature": {"en": "Air temperature (2 m)", "ar": "درجة حرارة الهواء (2 متر)"},
    "soil_moisture": {"en": "Soil moisture (0-10 cm)", "ar": "رطوبة التربة (0-10 سم)"},
    "precipitation": {"en": "Precipitation", "ar": "الأمطار"},
    "vegetation_greenness": {"en": "Vegetation greenness (NDVI)", "ar": "الغطاء النباتي (NDVI)"},
}

REGION_LABELS = {
    "nile_corridor": {"en": "the Nile corridor", "ar": "نطاق ممر النيل"},
    "morocco_comparison": {"en": "the Morocco comparison window", "ar": "نافذة المغرب للمقارنة"},
    "sahel_comparison": {"en": "the Sahel comparison window", "ar": "نافذة الساحل للمقارنة"},
}

PRODUCT_LABELS = {
    "M2TMNXSLV": "MERRA-2 T2M",
    "GLDAS_NOAH025_M": "GLDAS Noah SoilMoi0_10cm_inst",
    "GPM_3IMERGM": "GPM IMERG Monthly",
    "MOD13C2": "MODIS MOD13C2 NDVI",
}

SOURCE_TYPE_OF = {
    "M2TMNXSLV": "reanalysis",
    "GLDAS_NOAH025_M": "land_surface_model",
    "GPM_3IMERGM": "satellite_retrieval",
    "MOD13C2": "satellite_retrieval",
}

SOURCE_PHRASES = {
    "reanalysis": {
        "en": "a reanalysis product, not direct satellite observations",
        "ar": "منتج إعادة تحليل، وليس قياساً مباشراً من الأقمار الصناعية",
    },
    "land_surface_model": {
        "en": "a land-surface model output, not direct satellite observations",
        "ar": "مخرج نموذج سطح الأرض، وليس قياساً مباشراً من الأقمار الصناعية",
    },
    "satellite_retrieval": {
        "en": "a satellite-based retrieval product",
        "ar": "منتج استخلاص مبني على الأقمار الصناعية",
    },
}

INFERENCE_REASON_TEXTS = {
    "insufficient_sample_size": {
        "en": "the sample is too small to support a trend test (insufficient sample size)",
        "ar": "العينة غير كافية لإجراء اختبار الاتجاه (حجم عينة غير كافٍ)",
    },
    "all_cells_masked": {
        "en": "all cells were excluded by quality masking (all cells masked)",
        "ar": "كل الخلايا مستبعدة بفحص الجودة (كل الخلايا مقصاة)",
    },
    "zero_variance": {
        "en": "the series has zero variance in the selected period (zero variance)",
        "ar": "المتسلسلة ذات تباين صفري في الفترة المختارة (تباين صفري)",
    },
    "method_not_applicable": {
        "en": "the declared method is not applicable to this configuration (method not applicable)",
        "ar": "المنهجية المعلنة غير قابلة للتطبيق على هذا الإعداد (المنهجية غير قابلة للتطبيق)",
    },
    "inference_not_released": {
        "en": "inferential output is not released before the method review gate passes (inference not released)",
        "ar": "المخرجات الاستدلالية لا تُنشر قبل اجتياز بوابة مراجعة المنهجية (الاستدلال غير منشور)",
    },
}

RESULT_STATE_TEXTS = {
    "insufficient_data": {
        "en": "No conclusion is rendered: the analysis returned insufficient data. Nothing is invented or estimated.",
        "ar": "لا يُعرض استنتاج: نتيجة التحليل بيانات غير كافية. لا يتم اختراع أو تقدير أي قيم.",
    },
    "failed": {
        "en": "No conclusion is rendered: the analysis failed. Re-run the analysis or inspect the job error.",
        "ar": "لا يُعرض استنتاج: فشل التحليل. أعد تشغيل التحليل أو راجع خطأ المهمة.",
    },
}

DENOMINATOR_LABELS = {
    "eligible_cells": {"en": "eligible cells", "ar": "الخلايا المؤهلة"},
    "weighted_area": {"en": "the weighted AOI area", "ar": "مساحة نطاق التحليل الموزونة"},
}


class PayloadError(Exception):
    def __init__(self, errors):
        self.errors = list(errors)
        super().__init__("; ".join(self.errors))


def _fmt(value, decimals=3):
    number = float(value)
    text = f"{number:.{decimals}f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text in ("", "-", "-0"):
        text = "0"
    return text


def _pct(fraction, decimals=1):
    return f"{float(fraction) * 100:.{decimals}f}%"


def _normalize_period(period):
    if period is None:
        return None
    if isinstance(period, dict):
        start = period.get("start_month") or period.get("start")
        end = period.get("end_month") or period.get("end")
        if start is None or end is None:
            raise PayloadError(["period object requires start_month and end_month"])
        return (str(start), str(end))
    if isinstance(period, (list, tuple)):
        if len(period) != 2:
            raise PayloadError(["period sequence requires exactly two entries"])
        return (str(period[0]), str(period[1]))
    raise PayloadError(["period must be an object or a two-entry sequence"])


def _period_pair(payload):
    start, end = _normalize_period(payload["period"])
    return str(start), str(end)


def _require_number(value, errors, label):
    if value is None or isinstance(value, bool) or not isinstance(value, (int, float)):
        errors.append(f"{label} must be a number")


def validate_payload(payload):
    if not isinstance(payload, dict):
        raise PayloadError(["payload is not an object"])
    errors = []
    for fieldname in REQUIRED_FIELDS:
        if fieldname not in payload:
            errors.append(f"missing required field {fieldname}")
    if errors:
        raise PayloadError(errors)

    if payload["variable_id"] not in CANONICAL_VARIABLE_IDS:
        errors.append(f"unknown variable_id {payload['variable_id']!r}")
    if payload['region_id'] not in REGION_LABELS and not (
        isinstance(payload['region_id'], str) and payload['region_id'].strip() and
        isinstance(payload.get('region_label'), str) and payload['region_label'].strip()
    ):
        errors.append(f"unknown region_id {payload['region_id']!r}")
    if not isinstance(payload["units"], str) or not payload["units"].strip():
        errors.append("units must be a non-empty string")
    state = payload.get("result_state", "succeeded")
    if state not in RESULT_STATES:
        errors.append(f"unknown result_state {state!r}")

    product = payload["product"]
    if not isinstance(product, dict):
        errors.append("product must be an object")
    else:
        pid = product.get("product_id")
        if pid not in PRODUCT_LABELS:
            errors.append(f"unknown product_id {pid!r}")
        elif product.get("source_type") is not None and product["source_type"] != SOURCE_TYPE_OF[pid]:
            errors.append(
                f"source_type mismatch: payload claims {product['source_type']!r} but the registry "
                f"defines {SOURCE_TYPE_OF[pid]!r} for {pid}"
            )
        version = product.get("product_version")
        if not isinstance(version, str) or not version.strip():
            errors.append("product.product_version must be a non-empty string")

    regional = payload["regional"]
    if not isinstance(regional, dict):
        errors.append("regional must be an object")
        regional = {}
    _require_number(regional.get("mean"), errors, "regional.mean")
    n_months = regional.get("n_months")
    if not isinstance(n_months, int) or isinstance(n_months, bool) or n_months < 0:
        errors.append("regional.n_months must be a non-negative integer")
    slope = regional.get("sen_slope")
    if slope is not None:
        _require_number(slope, errors, "regional.sen_slope")
        if not isinstance(regional.get("slope_units"), str) or not regional["slope_units"].strip():
            errors.append("regional.slope_units is required when sen_slope is present")
    p_value = regional.get("p_value")
    alpha = regional.get("significance_alpha")
    if p_value is not None:
        _require_number(p_value, errors, "regional.p_value")
        if alpha is None:
            errors.append("regional.significance_alpha is required when p_value is present")
        else:
            _require_number(alpha, errors, "regional.significance_alpha")
            if not (0 < alpha < 1):
                errors.append("regional.significance_alpha must be between 0 and 1")
        reason = regional.get("inference_reason_code")
        if reason is not None:
            errors.append("inference_reason_code must be null when p_value is present")
    else:
        reason = regional.get("inference_reason_code")
        if reason not in INFERENCE_REASON_TEXTS:
            errors.append(
                f"regional.inference_reason_code is required when p_value is null and must be one of "
                f"{sorted(INFERENCE_REASON_TEXTS)}"
            )
    interval = regional.get("confidence_interval")
    if interval is not None:
        if not isinstance(interval, dict):
            errors.append("confidence_interval must be an object")
        else:
            _require_number(interval.get("low"), errors, "confidence_interval.low")
            _require_number(interval.get("high"), errors, "confidence_interval.high")
            if isinstance(interval.get("low"), (int, float)) and isinstance(interval.get("high"), (int, float)):
                if interval["low"] > interval["high"]:
                    errors.append("confidence_interval.low must not exceed high")

    cells = payload.get("cells")
    if cells is not None:
        if not isinstance(cells, dict):
            errors.append("cells must be an object")
        else:
            denominator = cells.get("denominator")
            if denominator not in DENOMINATORS:
                errors.append(f"cells.denominator must be one of {list(DENOMINATORS)}")
            ineligible = cells.get("ineligible_qa_cells")
            if not isinstance(ineligible, int) or isinstance(ineligible, bool) or ineligible < 0:
                errors.append("cells.ineligible_qa_cells must be a non-negative integer")
            if denominator == "eligible_cells":
                for key in ("total_cells", "eligible_cells", "increasing_cells", "decreasing_cells", "non_significant_cells"):
                    value = cells.get(key)
                    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                        errors.append(f"cells.{key} must be a non-negative integer for eligible_cells denominator")
                if all(isinstance(cells.get(k), int) for k in ("total_cells", "eligible_cells", "ineligible_qa_cells")):
                    if cells["eligible_cells"] + cells["ineligible_qa_cells"] != cells["total_cells"]:
                        errors.append("cell counts inconsistent: eligible + ineligible must equal total")
                if all(isinstance(cells.get(k), int) for k in ("increasing_cells", "decreasing_cells", "eligible_cells")):
                    if cells["increasing_cells"] + cells["decreasing_cells"] > cells["eligible_cells"]:
                        errors.append("cell counts inconsistent: significant cells exceed eligible cells")
            else:
                for key in ("increasing_weighted_fraction", "decreasing_weighted_fraction"):
                    fraction = cells.get(key)
                    if not isinstance(fraction, (int, float)) or isinstance(fraction, bool) or not (0 <= fraction <= 1):
                        errors.append(f"cells.{key} must be a fraction in [0, 1] for weighted_area denominator")

    coverage = payload.get("coverage")
    if coverage is not None:
        if not isinstance(coverage, dict):
            errors.append("coverage must be an object")
        else:
            fraction = coverage.get("valid_area_fraction")
            if not isinstance(fraction, (int, float)) or isinstance(fraction, bool) or not (0 <= fraction <= 1):
                errors.append("coverage.valid_area_fraction must be a fraction in [0, 1]")
            if coverage.get("denominator") not in DENOMINATORS:
                errors.append(f"coverage.denominator must be one of {list(DENOMINATORS)}")
            masked = coverage.get("ineligible_cells")
            if masked is not None and (not isinstance(masked, int) or isinstance(masked, bool) or masked < 0):
                errors.append("coverage.ineligible_cells must be a non-negative integer")

    sensitivity = payload.get("sensitivity")
    if sensitivity is not None:
        if not isinstance(sensitivity, dict):
            errors.append("sensitivity must be an object")
        else:
            matching = sensitivity.get("matching_windows")
            total = sensitivity.get("total_windows")
            if not isinstance(matching, int) or isinstance(matching, bool) or matching < 0:
                errors.append("sensitivity.matching_windows must be a non-negative integer")
            if not isinstance(total, int) or isinstance(total, bool) or total <= 0:
                errors.append("sensitivity.total_windows must be a positive integer")
            if isinstance(matching, int) and isinstance(total, int) and matching > total:
                errors.append("sensitivity.matching_windows must not exceed total_windows")

    comparison = payload.get("comparison")
    if comparison is not None:
        if not isinstance(comparison, dict):
            errors.append("comparison must be an object")
        else:
            regions = comparison.get("regions")
            if not isinstance(regions, list) or not regions or not all(isinstance(r, str) for r in regions):
                errors.append("comparison.regions must be a non-empty array of region ids")
            action = comparison.get("action")
            if action is not None and action not in (PERMITTED_ACTIONS | COMPARISON_ACTIONS):
                errors.append(
                    f"comparison.action {action!r} is not a schema-supported action; comparison "
                    f"actions are pending the Role 05/06 contract"
                )

    artifacts = payload.get("artifacts") or {}
    if not isinstance(artifacts, dict):
        errors.append("artifacts must be an object")
    else:
        for key, value in artifacts.items():
            if not isinstance(value, bool):
                errors.append(f"artifacts.{key} must be a boolean")
        if artifacts.get("receipt") and not payload.get("receipt_id"):
            errors.append("receipt_id is required when artifacts.receipt is true")

    if errors:
        raise PayloadError(errors)


class ActiveRequestTracker:
    def __init__(self):
        self.current = None
        self.superseded = set()

    def register(self, analysis_id, request_id, region_id, variable_ids, period):
        identity = {
            "analysis_id": analysis_id,
            "request_id": request_id,
            "region_id": region_id,
            "variable_ids": list(variable_ids),
            "period": _normalize_period(period),
        }
        if self.current is not None:
            self.superseded.add(self.current["request_id"])
        self.current = identity
        return dict(identity)

    def validate(self, payload):
        if self.current is None:
            return False, "stale_response: no active request registered"
        if (
            payload.get("request_id") == self.current["request_id"]
            and payload.get("analysis_id") == self.current["analysis_id"]
        ):
            if payload.get("region_id") != self.current["region_id"]:
                return False, "stale_response: region changed for the active request"
            if payload.get("variable_id") not in self.current["variable_ids"]:
                return False, "stale_response: variable changed for the active request"
            if _normalize_period(payload.get("period")) != self.current["period"]:
                return False, "stale_response: period changed for the active request"
            return True, None
        if payload.get("request_id") in self.superseded:
            return False, "stale_response: superseded by a newer request"
        return False, "stale_response: unknown request for the active session"


def _action(name, payload, target=None):
    return {
        "action": name,
        "analysis_id": payload["analysis_id"],
        "request_id": payload["request_id"],
        "target": target or {},
    }


def _identity_fields(payload):
    return {"analysis_id": payload["analysis_id"], "request_id": payload["request_id"]}


def _context_segment(payload, language):
    region = payload["region_id"]
    variable = payload["variable_id"]
    product = payload["product"]
    start, end = _period_pair(payload)
    pid = product["product_id"]
    source_type = SOURCE_TYPE_OF[pid]
    region_label = REGION_LABELS.get(region, {}).get(language, payload.get('region_label', region))
    if language == LANGUAGE_AR:
        text = (
            f"{VARIABLE_LABELS[variable]['ar']} على {region_label} "
            f"من {start} إلى {end}، استناداً إلى {PRODUCT_LABELS[pid]} "
            f"({pid} v{product['product_version']}) — {SOURCE_PHRASES[source_type]['ar']}."
        )
    else:
        text = (
            f"{VARIABLE_LABELS[variable]['en']} for {region_label} from {start} "
            f"to {end}, based on {PRODUCT_LABELS[pid]} ({pid} v{product['product_version']}) — "
            f"{SOURCE_PHRASES[source_type]['en']}."
        )
    segment = {"id": "context", "kind": "context", "text": text}
    segment.update(_identity_fields(payload))
    segment["actions"] = [_action("FOCUS_REGION", payload, {"region_id": region})]
    return segment


def _direction(slope):
    if slope > 0:
        return "increase", "زيادة"
    if slope < 0:
        return "decrease", "انخفاض"
    return "trend", "اتجاه"


def _regional_segment(payload, language):
    regional = payload["regional"]
    units = payload["units"]
    mean = _fmt(regional["mean"])
    n = regional["n_months"]
    slope = regional.get("sen_slope")
    p_value = regional.get("p_value")
    alpha = regional.get("significance_alpha")
    interval = regional.get("confidence_interval")
    reason = regional.get("inference_reason_code")
    slope_text = ""
    if slope is not None:
        slope_text = f"{_fmt(slope)} {regional['slope_units']}"
    if p_value is None:
        reason_text = INFERENCE_REASON_TEXTS[reason][language]
        if language == LANGUAGE_AR:
            text = (
                f"المتوسط الإقليمي {mean} {units} على مدار {n} قيمة شهرية (مخرج وصفي). "
                f"لم يُحسب الاستدلال: {reason_text}. لا يُطرح أي ادعاء بوجود اتجاه."
            )
        else:
            text = (
                f"Regional mean {mean} {units} over {n} monthly values (descriptive output). "
                f"Inference was not computed: {reason_text}. No trend claim is made."
            )
    elif alpha is not None and p_value >= alpha:
        slope_clause_ar = ""
        slope_clause_en = ""
        effect_ar = ""
        effect_en = ""
        if slope is not None:
            slope_clause_ar = f"ميل Sen {slope_text} مع "
            slope_clause_en = f"Sen's slope {slope_text} with "
            effect_ar = f" يُعرض الميل ({slope_text}) كحجم أثر فقط، وليس كاتجاه مثبت."
            effect_en = (
                f" The slope ({slope_text}) is reported as an effect size, not as an established trend."
            )
        if language == LANGUAGE_AR:
            text = (
                f"المتوسط الإقليمي {mean} {units} على مدار {n} قيمة شهرية (وصفي). "
                f"{slope_clause_ar}Mann-Kendall p = {_fmt(p_value)} ≥ alpha = {_fmt(alpha, 2)}: "
                f"الأدلة الإحصائية غير كافية على وجود اتجاه عام وفق المنهجية المعلنة.{effect_ar}"
            )
        else:
            text = (
                f"Regional mean {mean} {units} over {n} monthly values (descriptive). "
                f"{slope_clause_en}Mann-Kendall p = {_fmt(p_value)} >= alpha = {_fmt(alpha, 2)}: "
                f"insufficient statistical evidence for a trend under the declared method.{effect_en}"
            )
    else:
        direction_en, direction_ar = _direction(slope if slope is not None else 0)
        level = _fmt((1 - alpha) * 100, 0) if alpha is not None else "95"
        ci_text = ""
        if interval is not None:
            low, high = _fmt(interval["low"]), _fmt(interval["high"])
            if language == LANGUAGE_AR:
                ci_text = f" فاصل ثقة {level}% من {low} إلى {high} {units}."
            else:
                ci_text = f" {level}% confidence interval {low} to {high} {units}."
        method = payload.get("method_revision")
        method_suffix = f" ({method})" if method else ""
        slope_clause_ar = f"ميل Sen {slope_text} مع " if slope is not None else "مع "
        slope_clause_en = f"Sen's slope {slope_text} with " if slope is not None else "with "
        if language == LANGUAGE_AR:
            text = (
                f"المتوسط الإقليمي {mean} {units} على مدار {n} قيمة شهرية. {slope_clause_ar}"
                f"Mann-Kendall p = {_fmt(p_value)} < alpha = {_fmt(alpha, 2)}: أدلة إحصائية "
                f"معنوية على {direction_ar} وفق المنهجية المعلنة{method_suffix}.{ci_text}"
            )
        else:
            text = (
                f"Regional mean {mean} {units} over {n} monthly values. {slope_clause_en}"
                f"Mann-Kendall p = {_fmt(p_value)} < alpha = {_fmt(alpha, 2)}: statistically "
                f"significant evidence of {direction_en} under the declared method{method_suffix}.{ci_text}"
            )
    segment = {"id": "regional_trend", "kind": "regional_trend", "text": text}
    segment.update(_identity_fields(payload))
    artifacts = payload.get("artifacts") or {}
    segment["actions"] = []
    if artifacts.get("regional_chart"):
        segment["actions"].append(_action("FOCUS_REGIONAL_CHART", payload, {"variable_id": payload["variable_id"]}))
    return segment


def _cells_segment(payload, language):
    cells = payload["cells"]
    denominator = cells["denominator"]
    ineligible = cells["ineligible_qa_cells"]
    method = payload.get("method_revision")
    method_suffix = f" ({method})" if method else ""
    if denominator == "eligible_cells":
        eligible = cells["eligible_cells"]
        increasing = cells["increasing_cells"]
        decreasing = cells["decreasing_cells"]
        non_significant = cells["non_significant_cells"]
        pct_inc = _pct(increasing / eligible) if eligible else _pct(0)
        pct_dec = _pct(decreasing / eligible) if eligible else _pct(0)
        if language == LANGUAGE_AR:
            text = (
                f"أدلة على مستوى الخلايا وفق المنهجية المعلنة{method_suffix}: {increasing} خلية "
                f"تُظهر أدلة إحصائية على زيادة و{decreasing} خلية تُظهر أدلة إحصائية على انخفاض "
                f"({pct_inc} من {DENOMINATOR_LABELS[denominator]['ar']}: {increasing} من {eligible}؛ "
                f"و{pct_dec} من {DENOMINATOR_LABELS[denominator]['ar']}: {decreasing} من {eligible}). "
                f"و{ineligible} خلية غير مؤهلة مستبعدة بفحص الجودة. "
                f"بقية الخلايا ({non_significant}) لا تُظهر أدلة إحصائية معنوية محلية."
            )
        else:
            text = (
                f"Cell-level evidence under the declared method{method_suffix}: {increasing} cells "
                f"show statistical evidence of increase and {decreasing} cells show statistical "
                f"evidence of decrease ({pct_inc} of {DENOMINATOR_LABELS[denominator]['en']}: "
                f"{increasing} of {eligible}; {pct_dec} of {DENOMINATOR_LABELS[denominator]['en']}: "
                f"{decreasing} of {eligible}). {ineligible} ineligible cells were excluded by "
                f"quality screening. The remaining {non_significant} cells show no significant "
                f"local evidence."
            )
    else:
        inc_frac = _pct(cells["increasing_weighted_fraction"])
        dec_frac = _pct(cells["decreasing_weighted_fraction"])
        if language == LANGUAGE_AR:
            text = (
                f"أدلة على مستوى الخلايا وفق المنهجية المعلنة{method_suffix}: {inc_frac} من "
                f"{DENOMINATOR_LABELS[denominator]['ar']} تُظهر أدلة إحصائية على زيادة، و{dec_frac} "
                f"من {DENOMINATOR_LABELS[denominator]['ar']} تُظهر أدلة إحصائية على انخفاض. "
                f"و{ineligible} خلية غير مؤهلة مستبعدة بفحص الجودة من كل النسب."
            )
        else:
            text = (
                f"Cell-level evidence under the declared method{method_suffix}: {inc_frac} of "
                f"{DENOMINATOR_LABELS[denominator]['en']} shows statistical evidence of increase, "
                f"and {dec_frac} of {DENOMINATOR_LABELS[denominator]['en']} shows statistical "
                f"evidence of decrease. {ineligible} ineligible cells were excluded from every "
                f"share by quality screening."
            )
    segment = {"id": "cell_evidence", "kind": "cell_evidence", "text": text}
    segment.update(_identity_fields(payload))
    artifacts = payload.get("artifacts") or {}
    segment["actions"] = []
    if artifacts.get("cell_reveal"):
        segment["actions"].append(_action("REVEAL_CELLS", payload, {"variable_id": payload["variable_id"]}))
    return segment


def _coverage_segment(payload, language):
    coverage = payload["coverage"]
    fraction = _pct(coverage["valid_area_fraction"])
    denominator = coverage["denominator"]
    masked = coverage.get("ineligible_cells")
    if language == LANGUAGE_AR:
        text = (
            f"تغطية البيانات: {fraction} من {DENOMINATOR_LABELS[denominator]['ar']} تحتوي بيانات "
            f"صالحة (المقام: {denominator})."
        )
        if masked is not None:
            text += f" و{masked} خلية غير مؤهلة/مقصاة ومستبعدة من كل النسب."
    else:
        text = (
            f"Data coverage: {fraction} of {DENOMINATOR_LABELS[denominator]['en']} has valid data "
            f"(denominator: {denominator})."
        )
        if masked is not None:
            text += f" {masked} cells are ineligible/masked and excluded from every share."
    segment = {"id": "qa_coverage", "kind": "qa_coverage", "text": text}
    segment.update(_identity_fields(payload))
    segment["actions"] = []
    return segment


def _sensitivity_segment(payload, language):
    sensitivity = payload["sensitivity"]
    matching = sensitivity["matching_windows"]
    total = sensitivity["total_windows"]
    pct = _pct(matching / total)
    if language == LANGUAGE_AR:
        text = (
            f"ملخص الحساسية: {matching} من {total} نوافذ معادة التشغيل تتفق في إشارة الميل "
            f"({pct} من {total} نوافذ). هذا ملخص حساسية وصفي، وليس احتمالاً بصحة أي ادعاء."
        )
    else:
        text = (
            f"Sensitivity summary: {matching} of {total} re-run windows agree in slope sign "
            f"({pct} of {total} windows). This is a descriptive sensitivity summary, not a "
            f"probability that any claim is true."
        )
    segment = {"id": "sensitivity", "kind": "sensitivity", "text": text}
    segment.update(_identity_fields(payload))
    artifacts = payload.get("artifacts") or {}
    segment["actions"] = []
    if artifacts.get("spin_it"):
        segment["actions"].append(_action("OPEN_SPIN_IT", payload, {"variable_id": payload["variable_id"]}))
    return segment


def _comparison_segment(payload, language):
    comparison = payload["comparison"]
    regions = comparison["regions"]
    labels = []
    for region in regions:
        if region in REGION_LABELS:
            labels.append(REGION_LABELS[region][language])
        else:
            labels.append(region)
    region_text = ", ".join(labels)
    if language == LANGUAGE_AR:
        text = (
            f"بيانات مقارنة بين النطاقات متاحة لنفس المتغير والفترة والمنهجية: {region_text}. "
            f"الاختيار مُفصح عنه، ولا يُعد أي اتجاه معاكس مضموناً."
        )
    else:
        text = (
            f"Cross-region comparison data is attached for the same variable, period and method: "
            f"{region_text}. Selection is disclosed; no opposite trend is promised."
        )
    segment = {"id": "comparison", "kind": "comparison", "text": text}
    segment.update(_identity_fields(payload))
    segment["actions"] = []
    segment["action_pending_contract"] = True
    return segment


def _provenance_segment(payload, language):
    receipt_id = payload["receipt_id"]
    if language == LANGUAGE_AR:
        text = f"التوثيق الكامل وإعدادات المنهجية وبصمات المصادر متاحة في الإيصال {receipt_id}."
    else:
        text = f"Full provenance, method settings and source hashes are available in receipt {receipt_id}."
    segment = {"id": "provenance", "kind": "provenance", "text": text}
    segment.update(_identity_fields(payload))
    segment["actions"] = [_action("OPEN_RECEIPT", payload, {"receipt_id": receipt_id})]
    return segment


def render_conclusions(payload, language=LANGUAGE_EN, tracker=None):
    if language not in LANGUAGES:
        raise ValueError(f"unsupported language {language!r}; expected one of {list(LANGUAGES)}")
    validate_payload(payload)

    if tracker is not None:
        valid, reason = tracker.validate(payload)
        if not valid:
            return {
                "status": "stale_response",
                "reason_code": "stale_response",
                "reason": reason,
                "mode": MODE,
                "analysis_id": payload.get("analysis_id"),
                "request_id": payload.get("request_id"),
                "segments": [],
                "actions": [],
            }

    state = payload.get("result_state", "succeeded")
    if state != "succeeded":
        return {
            "status": state,
            "reason_code": payload.get("reason_code") or f"{state}_no_numeric_render",
            "message": RESULT_STATE_TEXTS[state][language],
            "mode": MODE,
            "analysis_id": payload["analysis_id"],
            "request_id": payload["request_id"],
            "segments": [],
            "actions": [],
        }

    artifacts = payload.get("artifacts") or {}
    segments = [_context_segment(payload, language), _regional_segment(payload, language)]
    if payload.get("cells") is not None:
        segments.append(_cells_segment(payload, language))
    if payload.get("coverage") is not None:
        segments.append(_coverage_segment(payload, language))
    if payload.get("sensitivity") is not None and artifacts.get("spin_it"):
        segments.append(_sensitivity_segment(payload, language))
    if payload.get("comparison") is not None:
        segments.append(_comparison_segment(payload, language))
    if artifacts.get("receipt") and payload.get("receipt_id"):
        segments.append(_provenance_segment(payload, language))

    actions = [action for segment in segments for action in segment["actions"]]
    return {
        "status": "succeeded",
        "mode": MODE,
        "language": language,
        "analysis_id": payload["analysis_id"],
        "request_id": payload["request_id"],
        "region_id": payload["region_id"],
        "variable_id": payload["variable_id"],
        "period": {"start_month": _period_pair(payload)[0], "end_month": _period_pair(payload)[1]},
        "units": payload["units"],
        "segments": segments,
        "actions": actions,
    }


def all_action_names(result):
    return sorted({action["action"] for segment in result["segments"] for action in segment["actions"]})

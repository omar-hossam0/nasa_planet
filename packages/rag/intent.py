from .arabic import tokenize, has_arabic, normalize_query
from .aliases import (
    NORMALIZED_ALIASES,
    PRODUCT_ALIASES,
    QUALIFIER_SOIL,
    QUALIFIER_AIR,
    OUT_OF_SCOPE_TOPICS,
    NEIGHBORHOOD_MARKERS,
    CROSS_GRID_MARKERS,
    CLARIFY_HUMIDITY,
    CLARIFY_WINTER,
    CLARIFY_TEMPERATURE,
    _norm,
)

STATUS_RECOMMENDED = "recommended"
STATUS_DOCUMENTED_ONLY = "documented_only"
STATUS_AMBIGUOUS = "ambiguous"
STATUS_UNSUPPORTED = "unsupported"
STATUS_UNAVAILABLE = "unavailable"

MAX_QUERY_CHARS = 1000

SEASON_TOKENS = {"شتاء", "الشتاء", "شتوي", "winter", "winters"}

PERCENT_TOKENS = {"نسبه", "نسبة", "percent", "%", "كام", "كم", "نسبتها", "نسبته", "percentage", "نسبة مئوية"}
CAUSE_TOKENS = {"ليه", "لماذا", "سبب", "because", "why", "سبب تاني", "عشان", "علشان", "ما سبب"}
COMPUTE_TOKENS = {"احسب", "اتجاه", "الاتجاه", "compute", "trend", "calculate", "estimate"}

YEAR_RE = __import__("re").compile(r"\b(1[89]\d{2}|20[0-4]\d)\b")


def _normalize_wordlist(words):
    out = set()
    for w in words:
        out.add(_norm(w) if has_arabic(w) else w.lower())
    return out


_SOIL_QUALIFIERS = _normalize_wordlist(QUALIFIER_SOIL["ar"]) | set(QUALIFIER_SOIL["en"])
_AIR_QUALIFIERS = _normalize_wordlist(QUALIFIER_AIR["ar"]) | set(QUALIFIER_AIR["en"])
_OUT_OF_SCOPE = {topic: _normalize_wordlist(data["ar"]) | set(data["en"]) for topic, data in OUT_OF_SCOPE_TOPICS.items()}
_NEIGHBORHOOD = _normalize_wordlist(NEIGHBORHOOD_MARKERS["ar"]) | set(NEIGHBORHOOD_MARKERS["en"])
_CROSS_GRID = _normalize_wordlist(CROSS_GRID_MARKERS["ar"]) | set(CROSS_GRID_MARKERS["en"])
_HUMIDITY = _normalize_wordlist(["رطوبة", "رطوبه", "الرطوبة", "الرطوبه", "humidity", "moisture"])
_SEASON = _normalize_wordlist(["شتاء", "الشتاء", "شتوي", "winter", "winters"])


def _tokens_of(query):
    toks = tokenize(query)
    return toks, set(toks)


def _match_aliases(tokens):
    found = set()
    token_set = set(tokens)
    for variable, langs in NORMALIZED_ALIASES.items():
        for lang, aliases in langs.items():
            for alias in aliases:
                if " " in alias:
                    parts = alias.split()
                    if all(p in token_set for p in parts):
                        found.add(variable)
                elif alias in token_set:
                    found.add(variable)
    return found


def _match_products(tokens):
    token_set = set(tokens)
    return {PRODUCT_ALIASES[t] for t in token_set if t in PRODUCT_ALIASES}


def _in(wordset, tokens):
    token_set = set(tokens)
    for w in wordset:
        if w in token_set:
            return True
        if " " in w:
            parts = w.split()
            if parts and all(p in token_set for p in parts):
                return True
    return False


def classify_query(query: str) -> dict:
    raw_query = query if isinstance(query, str) else ""
    if not raw_query.strip():
        return _unsupported(raw_query, "empty_query", "اكتب سؤال عن أحد المتغيرات الأربعة. Please ask about one of the four variables.")
    if len(raw_query) > MAX_QUERY_CHARS:
        return _unsupported(raw_query, "oversized_query", "السؤال طويل جداً. Query exceeds the supported length; shorten it to one question about the four variables.")

    tokens, _ = _tokens_of(raw_query)

    variables = _match_aliases(tokens)
    products = _match_products(tokens)

    if _in(_NEIGHBORHOOD, tokens):
        return _unsupported(
            raw_query,
            "unsupported_resolution",
            "الشبكة أكبر من مستوى الحي/الشارع؛ الدقة المحلية غير مدعومة. Analysis supports the defined regional windows, not neighborhood-level resolution.",
        )

    if _in(_CROSS_GRID, tokens):
        return _unsupported(
            raw_query,
            "cross_grid_comparison_requires_aggregation",
            "الشبكات الأصلية مختلفة بين المنتجات؛ المقارنة المباشرة بين خليتين من شبكتين مختلفتين غير صحيحة، وتحتاج تجميعاً مكانياً صريحاً. Native grids differ between products; comparing cells from different grids requires explicit spatial aggregation. A per-cell significance map also requires a fixed test family and multiplicity decision from the statistics service.",
        )

    years = [int(y) for y in YEAR_RE.findall(normalize_query(raw_query))]
    early_year = next((y for y in years if y < 2001 or y > 2024), None)
    if _in(_normalize_wordlist(['forecast', 'predict', 'prediction', 'تنبؤ', 'توقع', 'توقعات']), tokens):
        return _unsupported(raw_query, 'forecast_not_supported', 'Forecasting is not supported. التنبؤ بالمستقبل غير مدعوم.')
    if _in(_normalize_wordlist(['sea surface', 'ocean temperature', 'sea temperature', 'حرارة البحر', 'حرارة المحيط']), tokens):
        return _unsupported(raw_query, 'target_variable_not_available', 'Sea-surface temperature is outside the supported variables. حرارة سطح البحر غير مدعومة.')
    if not variables and _in(_normalize_wordlist(['drought', 'الجفاف', 'جفاف']), tokens):
        return {'status': STATUS_AMBIGUOUS, 'reason_code': 'drought_requires_variable',
                'variable_ids': [], 'suggested_variable_ids': [],
                'clarification': 'Do you mean precipitation, soil moisture or vegetation? هل تقصد الأمطار أم رطوبة التربة أم الغطاء النباتي؟'}

    humidity_present = _in(_HUMIDITY, tokens)
    soil_qualified = _in(_SOIL_QUALIFIERS, tokens)
    air_qualified = _in(_AIR_QUALIFIERS, tokens)

    if humidity_present and "soil_moisture" not in variables:
        if soil_qualified:
            variables.add("soil_moisture")
        elif air_qualified and not soil_qualified:
            return _unsupported(
                raw_query,
                "target_variable_not_available",
                "الرطوبة الجوية غير متاحة من المتغيرات الأربعة؛ رطوبة التربة (GLDAS) هي المتاح. Atmospheric humidity is not one of the four variables; soil moisture via GLDAS is available.",
            )
        else:
            return {
                "status": STATUS_AMBIGUOUS,
                "reason_code": "air_vs_soil_humidity",
                "clarification": CLARIFY_HUMIDITY,
                "variable_ids": [],
                "suggested_variable_ids": [],
                "display_text": raw_query,
            }

    if _in(_SEASON, tokens) and not variables and not products:
        return {
            "status": STATUS_AMBIGUOUS,
            "reason_code": "season_without_variable",
            "clarification": CLARIFY_WINTER,
            "variable_ids": [],
            "suggested_variable_ids": [],
            "note": "winter never auto-maps to precipitation",
            "display_text": raw_query,
        }

    if early_year is not None and (variables or products or _in(_normalize_wordlist(COMPUTE_TOKENS), tokens)):
        return {
            "status": STATUS_UNAVAILABLE,
            "reason_code": "period_outside_scope",
            "variable_ids": sorted(variables),
            "suggested_variable_ids": [],
            "note": f"year {early_year} is outside the verified 2001-2024 monthly window; nothing is computed or invented",
            "display_text": raw_query,
        }

    out_scope = None
    for topic, words in _OUT_OF_SCOPE.items():
        if _in(words, tokens):
            out_scope = topic
            break
    if out_scope and not variables and not products:
        return _unsupported(
            raw_query,
            "out_of_scope_topic",
            "الموضوع خارج نطاق المتغيرات الأربعة المدعومة (حرارة، رطوبة تربة، أمطار، غطاء نباتي). Topic is outside the four supported variables; no variable is guessed.",
            topic=out_scope,
        )

    if not variables and not products:
        return _unsupported(
            raw_query,
            "no_target_variable_identified",
            "لم يتم التعرف على متغير من المتغيرات الأربعة. No supported variable was identified; ask about air temperature, soil moisture, precipitation or vegetation greenness.",
        )

    variables |= products

    notes = []
    if "air_temperature" in variables:
        notes.append({"kind": "clarification", "text": CLARIFY_TEMPERATURE})
    if "soil_moisture" in variables and _in(_normalize_wordlist(PERCENT_TOKENS), tokens):
        notes.append(
            {
                "kind": "units_check",
                "text": (
                    "GLDAS SoilMoi0_10cm_inst وحدته kg m-2 وليست نسبة مئوية تلقائياً. "
                    "The GLDAS unit is kg m-2; it is not automatically a percentage."
                ),
            }
        )
    if _in(_normalize_wordlist(CAUSE_TOKENS), tokens):
        notes.append(
            {
                "kind": "causality_guard",
                "text": (
                    "ارتباط الاتجاه لا يثبت السببية. Trend association does not establish cause; "
                    "no causal explanation is generated from documentation."
                ),
            }
        )

    return {
        "status": None,
        "reason_code": None,
        "variable_ids": sorted(variables),
        "suggested_variable_ids": sorted(variables),
        "notes": notes,
        "display_text": raw_query,
        "tokens": tokens,
    }


def _unsupported(query, reason_code, message, topic=None):
    payload = {
        "status": STATUS_UNSUPPORTED,
        "reason_code": reason_code,
        "message": message,
        "variable_ids": [],
        "suggested_variable_ids": [],
        "display_text": query,
    }
    if topic:
        payload["topic"] = topic
    return payload

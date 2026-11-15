from .arabic import normalize_arabic_token, strip_diacritics

TEAM_AUTHORED_NOTE = (
    "Curated bilingual alias table authored by Role 04 (team-authored material), NOT official "
    "NASA content. Each alias entry links to the official source/product it points to; aliases "
    "must never be presented as NASA quotations."
)

ALIAS_PROVENANCE = {
    "air_temperature": {
        "official_source_ids": ["M2TMNXSLV", "MERRA2_README", "MERRA2_Specification"],
        "product": "M2TMNXSLV",
        "product_version": "5.12.4",
    },
    "soil_moisture": {
        "official_source_ids": ["GLDAS_NOAH025_M", "GLDAS", "GLDAS_Models"],
        "product": "GLDAS_NOAH025_M",
        "product_version": "2.1",
    },
    "precipitation": {
        "official_source_ids": ["GPM_3IMERGM", "IMERG_V07_ATBD"],
        "product": "GPM_3IMERGM",
        "product_version": "07",
    },
    "vegetation_greenness": {
        "official_source_ids": ["MOD13C2", "MOD13_User_Guide_V61"],
        "product": "MOD13C2",
        "product_version": "061",
    },
}


def _norm(word: str) -> str:
    stripped = strip_diacritics(word)
    return normalize_arabic_token(stripped)


VARIABLE_ALIASES = {
    "air_temperature": {
        "en": [
            "temperature",
            "air temperature",
            "2m temperature",
            "warming",
            "warming up",
            "heat",
            "hotter",
            "cold",
            "cooling",
            "trend of temperature",
        ],
        "ar": [
            "حرارة",
            "الحرارة",
            "درجة الحرارة",
            "حرارة الهواء",
            "حراره",
            "الحراره",
            "درجه الحراره",
            "سخونة",
            "سخونه",
            "بيسخن",
            "تسخن",
            "بتسخن",
            "احترار",
            "سخونية",
            "برد",
            "برده",
            "بيبرد",
        ],
    },
    "soil_moisture": {
        "en": [
            "soil moisture",
            "topsoil moisture",
            "soil water",
            "soil wetness",
            "surface soil moisture",
        ],
        "ar": [
            "رطوبة التربة",
            "رطوبه التربه",
            "التربه",
            "ماء التربة",
            "بلل التربة",
            "رطوبة الارض",
            "رطوبه الارض",
        ],
    },
    "precipitation": {
        "en": [
            "rain",
            "rainfall",
            "precipitation",
            "rain rate",
            "precip",
            "wet days",
        ],
        "ar": [
            "مطر",
            "هطول",
            "الهطول",
            "المطر",
            "أمطار",
            "امطار",
            "الأمطار",
            "تساقط",
            "الامطار",
            "مطرية",
        ],
    },
    "vegetation_greenness": {
        "en": [
            "ndvi",
            "vegetation",
            "greenness",
            "vegetation index",
            "plant greenness",
            "green cover",
        ],
        "ar": [
            "نباتات",
            "النباتات",
            "غطاء نباتي",
            "الغطاء النباتي",
            "خضارة",
            "الخضرة",
            "مساحات خضراء",
        ],
    },
}

NORMALIZED_ALIASES = {
    variable: {
        lang: sorted({_norm(a) if lang == "ar" else a.lower() for a in words})
        for lang, words in langs.items()
    }
    for variable, langs in VARIABLE_ALIASES.items()
}

PRODUCT_ALIASES = {
    "merra-2": "air_temperature",
    "merra2": "air_temperature",
    "merra": "air_temperature",
    "m2tmnxslv": "air_temperature",
    "gldas": "soil_moisture",
    "gldas_noah025_m": "soil_moisture",
    "gpm": "precipitation",
    "gpm_3imergm": "precipitation",
    "imerg": "precipitation",
    "modis": "vegetation_greenness",
    "mod13c2": "vegetation_greenness",
    "ndvi": "vegetation_greenness",
}

QUALIFIER_SOIL = {
    "ar": ["تربه", "التربه", "ارض", "الارض", "زراعيه"],
    "en": ["soil", "topsoil", "ground", "land"],
}

QUALIFIER_AIR = {
    "ar": ["هواء", "الهواء", "جو", "الجو", "جويه", "جوي"],
    "en": ["air", "atmospheric", "relative"],
}

OUT_OF_SCOPE_TOPICS = {
    "wind": {
        "en": ["wind", "winds", "wind speed", "windy"],
        "ar": ["رياح", "الرياح", "ريح", "سرعه الرياح"],
    },
    "earthquake": {
        "en": ["earthquake", "earthquakes", "seismic", "tremor"],
        "ar": ["زلزال", "زلازل", "الزلازل", "هزة أرضية"],
    },
    "sea_level": {
        "en": ["sea level", "sea-level rise", "ocean level", "tide"],
        "ar": ["مستوى سطح البحر", "مستوى البحر", "ارتفاع البحر", "المد والجزر"],
    },
    "solar_radiation": {
        "en": ["solar radiation", "sunlight", "irradiance", "insolation"],
        "ar": ["إشعاع شمسي", "الاشعاع الشمسي", "سطوع الشمس", "اشعاع"],
    },
    "ozone": {
        "en": ["ozone", "ozone layer", "uv index"],
        "ar": ["اوزون", "الأوزون", "طبقة الأوزون"],
    },
    "clouds": {
        "en": ["cloud cover", "cloudiness", "clouds"],
        "ar": ["سحب", "السحب", "غيوم", "الغيوم"],
    },
    "air_quality": {
        "en": ["air quality", "pollution", "pollutant", "aqi"],
        "ar": ["جودة الهواء", "تلوث", "التلوث", "ملوث"],
    },
    "crop_yield": {
        "en": ["crop yield", "harvest", "yield per hectare", "production tonnage"],
        "ar": ["محصول", "غلة", "المحصول", "إنتاجية الفدان", "إنتاج المحاصيل"],
    },
}

NEIGHBORHOOD_MARKERS = {
    "en": ["neighborhood", "neighbourhood", "my street", "my block", "this district", "this suburb"],
    "ar": ["حي", "الحي", "شارع", "الشارع", "العمارة"],
}

CROSS_GRID_MARKERS = {
    "en": [
        "compare cells", "two cells", "different grids", "pixel comparison", "compare pixels",
        "cell by cell", "grid comparison", "significance map",
    ],
    "ar": [
        "قارن خليتين", "مقارنة الخلايا", "خليتين", "شبكتين مختلفتين", "شبكتين", "مقارنة بكسل",
        "كل الخلايا", "خريطة دلالة",
    ],
}

CLARIFY_HUMIDITY = (
    "هل تقصد رطوبة التربة أم رطوبة الهواء؟ رطوبة التربة (GLDAS SoilMoi0_10cm_inst) هي المتغير "
    "المتاح من متغيراتنا الأربعة، أما الرطوبة الجوية (atmospheric humidity) فليست متاحاً. "
    "Did you mean soil moisture (available: GLDAS SoilMoi0_10cm_inst) or atmospheric humidity "
    "(not one of the four available variables)? Please clarify."
)

CLARIFY_WINTER = (
    "«شتاء» يشير إلى فصل/فترة زمنية، ولا يحدد المتغير. اختر المتغير المطلوب عن فترة الشتاء "
    "(درجة الحرارة، رطوبة التربة، الأمطار، الغطاء النباتي). Winter is a season/period, not a "
    "variable; no variable is selected automatically from it."
)

CLARIFY_TEMPERATURE = (
    "المتغير المتاح لدينا هو درجة حرارة الهواء على ارتفاع 2 متر (MERRA-2 T2M). درجة حرارة "
    "السطح/الأرض أو حرارة مدينة بعينها غير متاحة. The available variable is 2-metre air "
    "temperature (MERRA-2 T2M); surface/skin temperature or a specific city reading is not available."
)

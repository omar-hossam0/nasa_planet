"""Verified catalog snapshot used by the mock NASA data adapter.

Source of truth in this repository
----------------------------------
* ``docs/architecture/scope.v2.json`` - variable x region entries, bboxes,
  products, versions, coverage period and the readiness flags.
* ``data/nasa/runtime_catalog.json`` - legacy source-ingestion registry (T2M,
  SoilMoi0_10cm_inst) with units and native grid sizes.

The values below are a *snapshot* of those two files, copied so the backend can
run without reaching outside its own directory. Regenerate this module whenever
the data team publishes a new ``scope.v2.json``.

Known discrepancy
-----------------
``runtime_catalog.json`` describes the Egypt rectangle as ``[24, 22, 36, 32]``
while ``scope.v2.json`` defines ``nile_corridor`` as ``[29, 24, 33, 32]``. The
newer target scope wins here; the older bbox is recorded as a legacy alias in
``docs/OPEN_QUESTIONS.md``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

REGISTRY_SNAPSHOT = "scope.v2.json@2026-11-14 + runtime_catalog.json@2026-11-14"
DEFAULT_PERIOD_START = "2001-01"
DEFAULT_PERIOD_END = "2024-12"


@dataclass(frozen=True)
class VariableRecord:
    variable_id: str
    display_name: str
    description: str
    unit: str
    units_verified: bool
    unit_source: str
    product_id: str
    version: str
    source_variable: str
    provider: str
    documentation_url: str | None
    lineage_note: str
    aliases: tuple[str, ...] = field(default_factory=tuple)
    measurement_ready: bool = True
    method_ready: bool = False
    app_available: bool = False
    demo_available: bool = True
    coverage_start: str = DEFAULT_PERIOD_START
    coverage_end: str = DEFAULT_PERIOD_END
    native_grid: dict[str, int] | None = None
    limitations: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class RegionRecord:
    region_id: str
    display_name: str
    description: str
    bbox: tuple[float, float, float, float]
    period_start: str = DEFAULT_PERIOD_START
    period_end: str = DEFAULT_PERIOD_END
    aliases: tuple[str, ...] = field(default_factory=tuple)


_COMMON_LIMITATIONS = (
    "Native grids differ between products; no implicit regridding is performed.",
    "The study rectangle includes neighbouring land and sea; it is not a national mask.",
    "Missing values are missing, not zero.",
    "Trend association does not establish causation.",
)

VARIABLES: tuple[VariableRecord, ...] = (
    VariableRecord(
        variable_id="air_temperature",
        display_name="2-metre air temperature",
        description=(
            "Monthly mean 2-metre air temperature from the MERRA-2 monthly single-level "
            "product. Reanalysis output, not a station observation."
        ),
        unit="K",
        units_verified=True,
        unit_source="data/nasa/runtime_catalog.json (units field for T2M)",
        product_id="M2TMNXSLV",
        version="5.12.4",
        source_variable="T2M",
        provider="NASA GES DISC (MERRA-2)",
        documentation_url=None,
        lineage_note="Reanalysis product. Converted to degrees Celsius only for display.",
        aliases=("t2m", "temperature", "temp", "air_temp"),
        native_grid={"lat": 21, "lon": 19},
        limitations=_COMMON_LIMITATIONS,
    ),
    VariableRecord(
        variable_id="soil_moisture",
        display_name="Top 0-10 cm soil moisture",
        description=(
            "Monthly mean top-layer (0-10 cm) soil moisture from the GLDAS Noah land "
            "surface model. Model output, not a satellite retrieval."
        ),
        unit="kg m-2",
        units_verified=True,
        unit_source="data/nasa/runtime_catalog.json (units field for SoilMoi0_10cm_inst)",
        product_id="GLDAS_NOAH025_M",
        version="2.1",
        source_variable="SoilMoi0_10cm_inst",
        provider="NASA GES DISC (GLDAS Noah)",
        documentation_url=None,
        lineage_note="Land-surface model output. Not atmospheric humidity.",
        aliases=("soilmoi0_10cm_inst", "soil moisture", "soilmoisture", "sm"),
        native_grid={"lat": 40, "lon": 48},
        limitations=_COMMON_LIMITATIONS + ("Soil moisture is not atmospheric humidity.",),
    ),
    VariableRecord(
        variable_id="precipitation",
        display_name="Monthly precipitation rate",
        description=(
            "Monthly mean precipitation rate from the GPM IMERG monthly product."
        ),
        unit="mm day-1",
        units_verified=False,
        unit_source=(
            "Product documentation only. The unit is NOT asserted by a registry file in "
            "this repository, so it is flagged unverified."
        ),
        product_id="GPM_3IMERGM",
        version="07",
        source_variable="precipitation",
        provider="NASA GES DISC (GPM IMERG)",
        documentation_url=None,
        lineage_note="Satellite-gauge merged retrieval. Monthly means, not event totals.",
        aliases=("rain", "rainfall", "precip", "gpm_3imergm"),
        native_grid=None,
        limitations=_COMMON_LIMITATIONS
        + ("Monthly mean rate is not a monthly accumulation.",),
    ),
    VariableRecord(
        variable_id="vegetation_greenness",
        display_name="Vegetation greenness (NDVI)",
        description=(
            "Monthly NDVI composite from MODIS MOD13C2, used as a vegetation greenness "
            "indicator. NDVI is not crop yield."
        ),
        unit="1 (unitless index)",
        units_verified=False,
        unit_source=(
            "Product documentation only. The unit is NOT asserted by a registry file in "
            "this repository, so it is flagged unverified."
        ),
        product_id="MOD13C2",
        version="061",
        source_variable="CMG_0_05_Deg_Monthly_NDVI",
        provider="NASA LP DAAC (MODIS)",
        documentation_url=None,
        lineage_note="QA fields exist in the source product; QA filtering is not applied here.",
        aliases=("ndvi", "vegetation", "greenness", "veg"),
        native_grid=None,
        limitations=_COMMON_LIMITATIONS + ("NDVI is not crop yield.",),
    ),
)

REGIONS: tuple[RegionRecord, ...] = (
    RegionRecord(
        region_id="nile_corridor",
        display_name="Nile corridor (Egypt rectangle)",
        description=(
            "Egypt study rectangle used for the delivered temperature and soil-moisture "
            "cubes. Covers adjacent land and Mediterranean/Red Sea water."
        ),
        bbox=(29.0, 24.0, 33.0, 32.0),
        aliases=("egypt", "nile", "nile_corridor_egypt"),
    ),
    RegionRecord(
        region_id="morocco_comparison",
        display_name="Morocco comparison window",
        description="Comparison window for north-west Africa. Demo coverage only.",
        bbox=(-10.0, 30.0, -5.0, 35.0),
        aliases=("morocco", "morocco_window"),
    ),
    RegionRecord(
        region_id="sahel_comparison",
        display_name="Sahel comparison window",
        description="Comparison window for the west Sahel. Demo coverage only.",
        bbox=(-5.0, 12.0, 5.0, 17.0),
        aliases=("sahel", "sahel_window"),
    ),
)

VARIABLES_BY_ID: dict[str, VariableRecord] = {record.variable_id: record for record in VARIABLES}
REGIONS_BY_ID: dict[str, RegionRecord] = {record.region_id: record for record in REGIONS}

_ALIAS_TO_VARIABLE: dict[str, str] = {}
for _record in VARIABLES:
    _ALIAS_TO_VARIABLE[_record.variable_id.lower()] = _record.variable_id
    for _alias in _record.aliases:
        _ALIAS_TO_VARIABLE.setdefault(_alias.lower(), _record.variable_id)

_ALIAS_TO_REGION: dict[str, str] = {}
for _region in REGIONS:
    _ALIAS_TO_REGION[_region.region_id.lower()] = _region.region_id
    for _alias in _region.aliases:
        _ALIAS_TO_REGION.setdefault(_alias.lower(), _region.region_id)


def resolve_variable_id(value: str) -> str | None:
    """Map a user-supplied or legacy id/alias onto a canonical variable id."""
    return _ALIAS_TO_VARIABLE.get(value.strip().lower())


def resolve_region_id(value: str) -> str | None:
    return _ALIAS_TO_REGION.get(value.strip().lower())


def dataset_revision(variable_id: str, region_id: str) -> str:
    """Deterministic mock revision string. Not an official NASA revision id."""
    record = VARIABLES_BY_ID[variable_id]
    return f"{record.product_id}:{record.version}:{region_id}:mock"


def supported_region_ids(variable_id: str) -> list[str]:
    """Every configured region is declared for every variable in scope.v2.json."""
    if variable_id not in VARIABLES_BY_ID:
        return []
    return [region.region_id for region in REGIONS]

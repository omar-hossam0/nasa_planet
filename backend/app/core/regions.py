"""Validated, server-owned region allowlist. Adding an entry never enables real science."""
import json
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.schemas.common import Aoi, MonthStr

DEFAULT_REGIONS = Path(__file__).resolve().parents[2] / 'config' / 'regions.json'


class RegionConfig(BaseModel):
    model_config = ConfigDict(extra='forbid')
    region_id: str = Field(pattern=r'^[a-z][a-z0-9_]{0,63}$')
    display_name: str = Field(min_length=1)
    display_name_ar: str = ''
    description: str = ''
    bbox: tuple[float, float, float, float]
    period_start: MonthStr
    period_end: MonthStr
    aliases: tuple[str, ...] = ()
    supported_variable_ids: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode='after')
    def validate_region(self):
        Aoi(coordinates=list(self.bbox))
        if self.period_start > self.period_end:
            raise ValueError('Invalid region coverage period')
        return self


def load_regions(path=None):
    raw = json.loads(Path(path or DEFAULT_REGIONS).read_text(encoding='utf-8'))
    regions = [RegionConfig.model_validate(item) for item in raw['regions']]
    if not regions:
        raise ValueError('Region allowlist must not be empty')
    aliases = set()
    for region in regions:
        for alias in (region.region_id, *region.aliases):
            key = alias.strip().lower()
            if not key or key in aliases:
                raise ValueError('Region IDs and aliases must be unique')
            aliases.add(key)
    return regions

"""Mock NASA data adapter.

Serves variable metadata from the snapshot and regions from the validated
server configuration. It does not read NetCDF files, does not
touch the network, and does not claim measurement coverage beyond what the
registry snapshot states.
"""

from __future__ import annotations

from app.mocks import catalog as snapshot
from app.mocks.catalog import RegionRecord, VariableRecord


class MockNASADataAdapter:
    """Configured catalog reader used while real loaders are absent."""

    def __init__(self, regions_file=None):
        import hashlib
        import json
        from app.core.regions import load_regions
        configured = load_regions(regions_file)
        self._region_revision = hashlib.sha256(json.dumps([r.model_dump() for r in configured],
            sort_keys=True).encode()).hexdigest()[:16]
        self._regions = [RegionRecord(**r.model_dump()) for r in configured]
        self._by_id = {r.region_id: r for r in self._regions}
        self._aliases = {key.strip().lower(): r.region_id for r in self._regions for key in (r.region_id, *r.aliases)}
        for region in self._regions:
            if not set(region.supported_variable_ids) <= snapshot.VARIABLES_BY_ID.keys():
                raise ValueError('Region references an unknown variable')

    def list_variables(self) -> list[VariableRecord]:
        return list(snapshot.VARIABLES)

    def get_variable(self, variable_id: str) -> VariableRecord | None:
        return snapshot.VARIABLES_BY_ID.get(variable_id)

    def list_regions(self) -> list[RegionRecord]:
        return list(self._regions)

    def get_region(self, region_id: str) -> RegionRecord | None:
        return self._by_id.get(region_id)

    def resolve_variable_id(self, value: str) -> str | None:
        return snapshot.resolve_variable_id(value)

    def resolve_region_id(self, value: str) -> str | None:
        return self._aliases.get(value.strip().lower())

    def dataset_revision(self, variable_id: str, region_id: str) -> str:
        return snapshot.dataset_revision(variable_id, region_id).removesuffix(':mock') + ':' + self._region_revision + ':mock'

    def registry_snapshot(self) -> str:
        return snapshot.REGISTRY_SNAPSHOT + ':regions:' + self._region_revision

    # -- coverage helpers -------------------------------------------------
    def covers_period(self, variable_id: str, start_month: str, end_month: str) -> bool:
        record = self.get_variable(variable_id)
        if record is None:
            return False
        return record.coverage_start <= start_month and end_month <= record.coverage_end

    def supported_region_ids(self, variable_id: str) -> list[str]:
        return [r.region_id for r in self._regions if variable_id in r.supported_variable_ids]

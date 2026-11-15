"""Mock NASA data adapter.

Serves the verified catalog snapshot. It does not read NetCDF files, does not
touch the network, and does not claim measurement coverage beyond what the
registry snapshot states.
"""

from __future__ import annotations

from app.mocks import catalog as snapshot
from app.mocks.catalog import RegionRecord, VariableRecord


class MockNASADataAdapter:
    """Registry-backed catalog reader used while real loaders are absent."""

    def list_variables(self) -> list[VariableRecord]:
        return list(snapshot.VARIABLES)

    def get_variable(self, variable_id: str) -> VariableRecord | None:
        return snapshot.VARIABLES_BY_ID.get(variable_id)

    def list_regions(self) -> list[RegionRecord]:
        return list(snapshot.REGIONS)

    def get_region(self, region_id: str) -> RegionRecord | None:
        return snapshot.REGIONS_BY_ID.get(region_id)

    def resolve_variable_id(self, value: str) -> str | None:
        return snapshot.resolve_variable_id(value)

    def resolve_region_id(self, value: str) -> str | None:
        return snapshot.resolve_region_id(value)

    def dataset_revision(self, variable_id: str, region_id: str) -> str:
        return snapshot.dataset_revision(variable_id, region_id)

    def registry_snapshot(self) -> str:
        return snapshot.REGISTRY_SNAPSHOT

    # -- coverage helpers -------------------------------------------------
    def covers_period(self, variable_id: str, start_month: str, end_month: str) -> bool:
        record = self.get_variable(variable_id)
        if record is None:
            return False
        return record.coverage_start <= start_month and end_month <= record.coverage_end

    def supported_region_ids(self, variable_id: str) -> list[str]:
        return snapshot.supported_region_ids(variable_id)

"""Adapter contracts for the future real integrations.

Routers and services depend on these protocols, never on concrete classes, so a
real NASA loader / statistics engine / RAG service can replace the mock without
touching the HTTP layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from app.mocks.catalog import RegionRecord, VariableRecord
from app.schemas.analysis import AnalysisSpec
from app.schemas.common import ApiWarning, Language
from app.schemas.results import DatasetRevision, MethodRef, VariableResult
from app.schemas.spin import SpinRequest, SpinSummary, SpinWindow


@dataclass
class ComputedAnalysis:
    """Numeric payload returned by a statistics adapter."""

    variables: list[VariableResult]
    method: MethodRef
    datasets: list[DatasetRevision]
    warnings: list[ApiWarning]


@dataclass
class ComputedSpin:
    windows: list[SpinWindow]
    summary: SpinSummary
    warnings: list[ApiWarning]


@runtime_checkable
class NASADataAdapter(Protocol):
    """Read-only view over the verified dataset registry."""

    def list_variables(self) -> list[VariableRecord]: ...

    def get_variable(self, variable_id: str) -> VariableRecord | None: ...

    def list_regions(self) -> list[RegionRecord]: ...

    def get_region(self, region_id: str) -> RegionRecord | None: ...

    def resolve_variable_id(self, value: str) -> str | None: ...

    def resolve_region_id(self, value: str) -> str | None: ...

    def dataset_revision(self, variable_id: str, region_id: str) -> str: ...

    def registry_snapshot(self) -> str: ...


@runtime_checkable
class StatisticsAdapter(Protocol):
    """Executes approved statistical work. Mock returns fixtures today."""

    def compute_analysis(self, spec: AnalysisSpec, *, result_id: str) -> ComputedAnalysis: ...

    def compute_spin(
        self, spec: AnalysisSpec, *, result_id: str, request: SpinRequest
    ) -> ComputedSpin: ...


@runtime_checkable
class RAGAdapter(Protocol):
    """Recommendations and grounded explanations."""

    def recommend(self, question: str, language: Language): ...

    def explain(self, result, language: Language): ...

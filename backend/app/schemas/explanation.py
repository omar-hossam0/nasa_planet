"""Explanation schemas.

Explanations are template-rendered from fields already stored in the result.
No model is called, so no new numbers and no citations are introduced.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import DISCLAIMER, DataMode, Language


class ExplanationMode(str, Enum):
    mock_template = "mock_template"
    local_retrieval = "local_retrieval"
    llm = "llm"


class UiActionId(str, Enum):
    """Proposed UI action identifiers. Pending frontend confirmation."""

    FOCUS_REGION = "FOCUS_REGION"
    FOCUS_REGIONAL_CHART = "FOCUS_REGIONAL_CHART"
    REVEAL_CELLS = "REVEAL_CELLS"
    OPEN_SPIN_IT = "OPEN_SPIN_IT"
    OPEN_RECEIPT = "OPEN_RECEIPT"


class ExplanationRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"example": {"result_id": "result_mock_example", "language": "en"}},
    )

    result_id: str = Field(min_length=1, max_length=128)
    language: Language = Language.en


class ExplanationSection(BaseModel):
    section_id: str
    title: str
    body: str


class UiAction(BaseModel):
    action_id: UiActionId
    label: str
    enabled: bool = True
    payload: dict[str, Any] = Field(default_factory=dict)


class ExplanationResponse(BaseModel):
    explanation_id: str
    result_id: str
    language: Language
    mode: ExplanationMode = ExplanationMode.mock_template
    sections: list[ExplanationSection]
    actions: list[UiAction] = Field(default_factory=list)
    references: list[str] = Field(
        default_factory=list,
        description="Verified source references. Empty because no retrieval ran.",
    )
    limitations: list[str] = Field(default_factory=list)
    data_mode: DataMode = DataMode.mock
    disclaimer: str = DISCLAIMER
    generated_at: str

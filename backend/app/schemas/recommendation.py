"""Recommendation schemas (mock rule engine today, RAG adapter later)."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import DISCLAIMER, DataMode, Language, MonthStr


class RecommendationStatus(str, Enum):
    recommended = "recommended"
    clarification_required = "clarification_required"
    unsupported = "unsupported"


class RecommendationRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "question": "I want to study temperature changes.",
                "language": "en",
                "region_id": "nile_corridor",
                "start_month": "2005-01",
                "end_month": "2020-12",
            }
        },
    )

    question: str = Field(min_length=3, max_length=1000)
    language: Language = Language.en
    region_id: str | None = Field(default=None, max_length=64)
    start_month: MonthStr | None = None
    end_month: MonthStr | None = None

    @field_validator("question")
    @classmethod
    def _strip_question(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 3:
            raise ValueError("question must contain at least 3 non-space characters")
        return cleaned


class CandidateVariable(BaseModel):
    variable_id: str
    display_name: str
    unit: str
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    demo_available: bool
    measurement_ready: bool


class RecommendationContext(BaseModel):
    region_id: str | None = None
    region_known: bool | None = None
    start_month: str | None = None
    end_month: str | None = None


class RecommendationResponse(BaseModel):
    """Deterministic recommendation output.

    ``provider`` is ``mock_rules``: no model was called and no source document
    was retrieved, therefore ``references`` is always empty here.
    """

    status: RecommendationStatus
    question: str
    language: Language
    candidates: list[CandidateVariable] = Field(default_factory=list)
    clarification_question: str | None = None
    message: str
    context: RecommendationContext = Field(default_factory=RecommendationContext)
    references: list[str] = Field(
        default_factory=list, description="Retrieved source references. Always empty in mock mode."
    )
    provider: str = "mock_rules"
    data_mode: DataMode = DataMode.mock
    disclaimer: str = DISCLAIMER
    warnings: list[str] = Field(default_factory=list)

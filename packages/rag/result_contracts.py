"""Traceable, rule-based interpretation of one stored variable result."""
from typing import Literal
from pydantic import BaseModel, Field
from .judge import InferenceEvidence


class AssessmentReason(BaseModel):
    code: str
    severity: Literal['info', 'warning', 'blocking']
    message: str


class AssessmentFacts(BaseModel):
    slope_per_year: float | None = None
    slope_unit: str | None = None
    mean_monthly_value: float | None = None
    monthly_unit: str
    mean_celsius: float | None = None
    valid_months: int = 0
    complete_years: int = 0
    retained_cells: int | None = None
    selected_cells: int | None = None
    retained_area_fraction: float | None = None
    leave_one_year_out_min_slope: float | None = None
    leave_one_year_out_max_slope: float | None = None
    leave_one_year_out_same_sign_count: int | None = None
    leave_one_year_out_windows: int | None = None


class ResultAssessment(BaseModel):
    policy_revision: str
    result_id: str
    variable_id: str
    descriptive_status: Literal['available', 'insufficient_data', 'inconsistent_result']
    inference_status: Literal['not_available'] = 'not_available'
    diagnostics_status: Literal['not_run_for_this_result'] = 'not_run_for_this_result'
    direction: Literal['increase', 'decrease', 'no_estimated_change', 'unavailable']
    headline: str
    reasons: list[AssessmentReason] = Field(default_factory=list)
    facts: AssessmentFacts
    inference: InferenceEvidence = Field(default_factory=lambda: InferenceEvidence(status='not_computed', reason_code='inference_not_released'))
    judgment: dict = Field(default_factory=dict)
    region_id: str | None = None
    start_month: str | None = None
    end_month: str | None = None
    source_product_id: str | None = None
    source_product_version: str | None = None

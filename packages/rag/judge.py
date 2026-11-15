"""Deterministic interpretation, conditional on an explicitly released method registry."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class InferenceEvidence(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    status: Literal['not_computed', 'insufficient_data', 'computed', 'failed']
    method_id: str | None = None
    method_revision: str | None = None
    validation_id: str | None = None
    estimand: str | None = None
    p_value: float | None = Field(default=None, ge=0, le=1)
    alpha: float = Field(default=.05, gt=0, lt=1)
    confidence_level: float | None = Field(default=None, gt=0, lt=1)
    interval: tuple[float, float] | None = None
    reason_code: str | None = None

    @model_validator(mode='after')
    def coherent(self):
        if self.status == 'computed' and (self.p_value is None or not all([self.method_id, self.method_revision, self.validation_id, self.estimand])):
            raise ValueError('Computed inference needs a probability and traceable method/validation/estimand')
        if self.status != 'computed' and (self.p_value is not None or self.interval is not None):
            raise ValueError('Unavailable inference cannot carry numeric inference')
        if self.status != 'computed' and not self.reason_code:
            raise ValueError('Unavailable inference requires an explicit reason')
        if (self.interval is None) != (self.confidence_level is None):
            raise ValueError('Interval and confidence level must be supplied together')
        if self.interval is not None and self.interval[0] > self.interval[1]:
            raise ValueError('Reversed interval')
        return self


# No method has scientific release approval. Tests inject a synthetic registry;
# production never registers a method merely because a p-value was supplied.
RELEASED_METHODS = {}


def judge_inference(evidence, language='en', released_methods=None):
    registry = RELEASED_METHODS if released_methods is None else released_methods
    key = (evidence.method_id, evidence.method_revision, evidence.validation_id, evidence.estimand)
    state = ('unavailable' if evidence.status != 'computed' else
             'unreleased_method' if registry.get(key) is not True else
             'evidence_against_zero' if evidence.p_value < evidence.alpha else 'insufficient_evidence')
    messages = {
        'unavailable': ('Statistical inference is unavailable; no significance conclusion is made.', 'الاستدلال الإحصائي غير متاح؛ لا يصدر حكم بالدلالة.'),
        'unreleased_method': ('The supplied method has no release approval; its p-value cannot support a significance claim.', 'الطريقة المرسلة غير معتمدة للإصدار؛ لا تُستخدم قيمة p لإعلان الدلالة.'),
        'evidence_against_zero': ('The declared test provides evidence against its zero-trend null at the declared threshold; this does not establish cause.', 'الاختبار المعلن يقدم دليلًا ضد فرضية الاتجاه الصفري عند العتبة المعلنة؛ ولا يثبت السببية.'),
        'insufficient_evidence': ('The declared test provides insufficient evidence against its zero-trend null; this does not prove stability.', 'الأدلة غير كافية لرفض فرضية الاتجاه الصفري وفق الاختبار المعلن؛ وهذا لا يثبت الاستقرار.')}
    return {'state': state, 'message': messages[state][language == 'ar'], 'method_id': evidence.method_id,
            'alpha': evidence.alpha, 'p_value': evidence.p_value if registry.get(key) is True else None}

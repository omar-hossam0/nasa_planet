"""Grounded documentation recommendations and result-only Role04 conclusions."""

from dataclasses import dataclass, field
from statistics import mean

from app.mocks.ai import RecommendationOutcome
from app.schemas.recommendation import RecommendationStatus
from app.schemas.explanation import UiAction, UiActionId
from app.adapters.science import DISCLAIMER
from packages.rag.facade import Role04Service
from packages.rag.intent import classify_query
from packages.rag.retriever import Retriever
from app.services.result_assessment import assess_variable


@dataclass
class Rendered:
    sections: list
    actions: list
    limitations: list
    references: list
    mode: str = "conclusion_templates"
    assessments: list = field(default_factory=list)


class ScienceRAGAdapter:
    provider_name = "curated_aliases"

    def __init__(self):
        self.retriever = Retriever()

    def recommend(self, question, language):
        result = classify_query(question)
        ids = result.get("variable_ids", [])
        state = (
            RecommendationStatus.recommended
            if ids
            else (
                RecommendationStatus.clarification_required
                if result["status"] == "ambiguous"
                else RecommendationStatus.unsupported
            )
        )
        return RecommendationOutcome(
            status=state,
            variable_ids=ids,
            confidence={v: 1.0 for v in ids},
            clarification_question=result.get("clarification"),
        )

    def explain(self, result, language):
        sections, references, limitations, assessments = [], [], [DISCLAIMER], []
        for variable in result.variables:
            artifact = result.science[variable.variable_id]
            meta = artifact["metadata"]
            dataset = next(
                d for d in result.datasets if d.variable_id == variable.variable_id
            )
            valid = [p.value for p in variable.series if p.value is not None]
            payload = {
                "analysis_id": result.result_id,
                "request_id": result.job_id,
                "region_id": result.analysis.region_id,
                "region_label": result.analysis.region_display_name,
                "variable_id": variable.variable_id,
                "period": {
                    "start_month": result.analysis.start_month,
                    "end_month": result.analysis.end_month,
                },
                "units": variable.unit,
                "product": {
                    "product_id": dataset.product_id,
                    "product_version": dataset.version,
                },
                "regional": {
                    "mean": mean(valid) if valid else 0,
                    "n_months": len(valid),
                    "sen_slope": variable.trend.slope_per_year,
                    "slope_units": variable.trend.slope_unit,
                    "p_value": None,
                    "inference_reason_code": "inference_not_released",
                },
                "result_state": "succeeded" if valid else "insufficient_data",
                "receipt_id": result.receipt_id,
                "artifacts": {
                    "regional_chart": True,
                    "cell_reveal": True,
                    "receipt": True,
                },
            }
            # Fresh facade/tracker per call; share only immutable retrieval index.
            role04 = Role04Service(retriever=self.retriever)
            rendered = role04.render_result(
                payload, language=language.value, normalize=False
            )
            titles = ({"context": "المصدر والفترة", "provenance": "إيصال الأدلة"}
                      if language.value == "ar" else
                      {"context": "Source and period", "provenance": "Evidence receipt"})
            sections.extend((f'{variable.variable_id}_{part["id"]}',
                             titles.get(part["id"], part["id"]), part["text"])
                            for part in rendered.get("segments", [])
                            if part["id"] in ("context", "provenance"))
            assessment = assess_variable(result, variable, language)
            assessments.append(assessment)
            sections.extend(role04.render_assessment(assessment, language))
            limitations.extend(reason.message for reason in assessment.reasons)
            limitations.extend(meta["warnings"])
            evidence = self.retriever.answer_query(
                variable.variable_id.replace("_", " ")
            )
            references.extend(c["source_url"] for c in evidence.get("citations", []))
        actions = [
            UiAction(
                action_id=UiActionId.OPEN_RECEIPT,
                label="Evidence receipt",
                payload={"receipt_id": result.receipt_id},
            )
        ]
        return Rendered(
            sections,
            actions,
            list(dict.fromkeys(limitations)),
            list(dict.fromkeys(references)),
            assessments=assessments,
        )

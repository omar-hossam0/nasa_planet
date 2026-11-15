"""Grounded documentation recommendations and result-only Role04 conclusions."""

from dataclasses import dataclass
from statistics import mean

from app.mocks.ai import RecommendationOutcome
from app.schemas.recommendation import RecommendationStatus
from app.schemas.explanation import UiAction, UiActionId
from app.adapters.science import DISCLAIMER
from packages.rag.facade import Role04Service
from packages.rag.intent import classify_query
from packages.rag.retriever import Retriever


@dataclass
class Rendered:
    sections: list
    actions: list
    limitations: list
    references: list
    mode: str = "conclusion_templates"


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
        sections, references, limitations = [], [], [DISCLAIMER]
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
            rendered = Role04Service(retriever=self.retriever).render_result(
                payload, language=language.value, normalize=False
            )
            titles = (
                {
                    "context": "المصدر والفترة",
                    "regional_trend": "القيم الشهرية وحدود الاستدلال",
                    "provenance": "إيصال الأدلة",
                }
                if language.value == "ar"
                else {
                    "context": "Source and period",
                    "regional_trend": "Monthly values and inference limits",
                    "provenance": "Evidence receipt",
                }
            )
            sections.extend(
                (
                    f'{variable.variable_id}_{s["id"]}',
                    titles.get(s["id"], s["id"]),
                    s["text"],
                )
                for s in rendered["segments"]
            )
            if not valid:
                sections.append(
                    (
                        variable.variable_id + "_missing",
                        "Insufficient data",
                        rendered["message"],
                    )
                )
            if variable.trend.slope_per_year is not None:
                body = (
                    f"Annual descriptive Theil–Sen slope: {variable.trend.slope_per_year:.8g} {variable.trend.slope_unit}. "
                    f"{variable.trend.n_years} valid annual observations. Positive/negative cell slopes are not significance classifications."
                    if language.value == "en"
                    else f"ميل Theil–Sen السنوي الوصفي: {variable.trend.slope_per_year:.8g} {variable.trend.slope_unit}. عدد السنوات الصالحة {variable.trend.n_years}. إشارة ميل الخلايا لا تعني دلالة إحصائية."
                )
                sections.append(
                    (
                        variable.variable_id + "_annual",
                        "Annual descriptive estimate",
                        body,
                    )
                )
            body = (
                f"QA retained {meta['eligible_fixed_support_cells']} of {meta['selected_cell_count']} selected cells "
                f"({meta['fixed_support_area_fraction_of_selected_native_cells']*100:.2f}% of selected native-cell area). "
                f"Positive slopes: {artifact['positive_cells']}; negative slopes: {artifact['negative_cells']}. No significance test was released."
            )
            if language.value == 'ar':
                body = (f"احتفظ فحص الجودة بـ{meta['eligible_fixed_support_cells']} من {meta['selected_cell_count']} خلية مختارة، "
                    f"تمثل {meta['fixed_support_area_fraction_of_selected_native_cells']*100:.2f}% من مساحة الخلايا الأصلية المختارة. "
                    f"الخلايا ذات الميل الموجب: {artifact['positive_cells']}، والسالب: {artifact['negative_cells']}. لم يُنشر اختبار دلالة إحصائية.")
            sections.append(
                (variable.variable_id + "_support", "QA and native-grid support", body)
            )
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
        )

"""Deterministic mock AI behaviour: recommendations and explanations.

No model, embedding or retrieval runs here. Recommendations are keyword rules;
explanations are templates filled from fields already present in the stored
result. That is why ``references`` is always empty - inventing citations would
be worse than returning none.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from app.schemas.common import Language
from app.schemas.explanation import UiAction, UiActionId
from app.schemas.recommendation import RecommendationStatus
from app.schemas.results import ResultResponse

_TASHKEEL = re.compile(r"[\u064B-\u0652\u0670\u0640]")
_NON_WORD = re.compile(r"[^\w\u0600-\u06FF\s-]+", re.UNICODE)


def normalize_text(text: str) -> str:
    """Lower-case + Arabic-aware normalisation used for keyword matching.

    Removes diacritics and tatweel and unifies alef/ya variants. Deliberately
    does not strip or rewrite letters that change meaning.
    """
    lowered = unicodedata.normalize("NFKC", text).lower()
    lowered = _TASHKEEL.sub("", lowered)
    lowered = (
        lowered.replace("\u0623", "\u0627")
        .replace("\u0625", "\u0627")
        .replace("\u0622", "\u0627")
        .replace("\u0649", "\u064a")
        .replace("\u0629", "\u0647")
    )
    lowered = _NON_WORD.sub(" ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


# ---------------------------------------------------------------------------
# Recommendation rules
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class KeywordRule:
    variable_id: str
    specific: tuple[str, ...]
    generic: tuple[str, ...] = ()


RULES: tuple[KeywordRule, ...] = (
    KeywordRule(
        variable_id="air_temperature",
        specific=(
            "air temperature",
            "temperature",
            "temp",
            "warming",
            "heat",
            "\u062f\u0631\u062c\u0647 \u0627\u0644\u062d\u0631\u0627\u0631\u0647",
            "\u062d\u0631\u0627\u0631\u0647",
            "\u0633\u062e\u0648\u0646\u0647",
        ),
    ),
    KeywordRule(
        variable_id="soil_moisture",
        specific=(
            "soil moisture",
            "soil water",
            "\u0631\u0637\u0648\u0628\u0647 \u0627\u0644\u062a\u0631\u0628\u0647",
            "\u062a\u0631\u0628\u0647",
            "soil",
        ),
        generic=("moisture", "humidity", "\u0631\u0637\u0648\u0628\u0647"),
    ),
    KeywordRule(
        variable_id="precipitation",
        specific=(
            "precipitation",
            "rainfall",
            "rain",
            "\u0627\u0645\u0637\u0627\u0631",
            "\u0645\u0637\u0631",
            "\u0647\u0637\u0648\u0644",
        ),
    ),
    KeywordRule(
        variable_id="vegetation_greenness",
        specific=(
            "vegetation",
            "greenness",
            "ndvi",
            "plant",
            "\u063a\u0637\u0627\u0621 \u0646\u0628\u0627\u062a\u064a",
            "\u0646\u0628\u0627\u062a",
            "\u062e\u0636\u0631\u0647",
        ),
    ),
)

CLARIFICATION_EN = (
    "Did you mean soil moisture (top 0-10 cm) or atmospheric humidity? "
    "This demo only has a soil-moisture variable; atmospheric humidity is not in scope."
)
CLARIFICATION_AR = (
    "\u0647\u0644 \u062a\u0642\u0635\u062f \u0631\u0637\u0648\u0628\u0629 \u0627\u0644\u062a\u0631\u0628\u0629 "
    "(\u0645\u0646 0 \u0625\u0644\u0649 10 \u0633\u0645) \u0623\u0645 \u0627\u0644\u0631\u0637\u0648\u0628\u0629 "
    "\u0627\u0644\u062c\u0648\u064a\u0629\u061f \u0647\u0630\u0627 \u0627\u0644\u0639\u0631\u0636 "
    "\u064a\u062d\u062a\u0648\u064a \u0639\u0644\u0649 \u0645\u062a\u063a\u064a\u0631 \u0631\u0637\u0648\u0628\u0629 "
    "\u0627\u0644\u062a\u0631\u0628\u0629 \u0641\u0642\u0637."
)

RATIONALE: dict[str, str] = {
    "air_temperature": "The question mentions temperature or warming.",
    "soil_moisture": "The question mentions soil moisture or soil water.",
    "precipitation": "The question mentions rain, rainfall or precipitation.",
    "vegetation_greenness": "The question mentions vegetation, greenness or NDVI.",
}


@dataclass(frozen=True)
class RecommendationOutcome:
    status: RecommendationStatus
    variable_ids: list[str]
    confidence: dict[str, float]
    clarification_question: str | None


def recommend(question: str, language: Language) -> RecommendationOutcome:
    """Deterministic keyword recommendation. Returns catalog variable ids only."""
    text = normalize_text(question)
    scores: dict[str, float] = {}
    generic_only: set[str] = set()

    for rule in RULES:
        score = 0.0
        matched_specific = False
        for keyword in rule.specific:
            if normalize_text(keyword) and normalize_text(keyword) in text:
                score += 2.0 if " " in keyword.strip() else 1.0
                matched_specific = True
        for keyword in rule.generic:
            if normalize_text(keyword) and normalize_text(keyword) in text:
                score += 1.0
        if score > 0:
            scores[rule.variable_id] = score
            if not matched_specific:
                generic_only.add(rule.variable_id)

    if not scores:
        return RecommendationOutcome(
            status=RecommendationStatus.unsupported,
            variable_ids=[],
            confidence={},
            clarification_question=None,
        )

    best_id = max(scores, key=lambda key: scores[key])
    best_score = scores[best_id]

    # A generic term alone (e.g. bare "moisture" / "رطوبة") is ambiguous.
    if best_id in generic_only and len(scores) == 1:
        return RecommendationOutcome(
            status=RecommendationStatus.clarification_required,
            variable_ids=[],
            confidence={},
            clarification_question=CLARIFICATION_AR if language is Language.ar else CLARIFICATION_EN,
        )

    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    confidence = {variable_id: round(min(0.95, 0.55 + 0.1 * score), 2) for variable_id, score in ordered}
    return RecommendationOutcome(
        status=RecommendationStatus.recommended,
        variable_ids=[variable_id for variable_id, _ in ordered],
        confidence=confidence,
        clarification_question=None,
    )


# ---------------------------------------------------------------------------
# Explanation templates
# ---------------------------------------------------------------------------
_DIRECTION_EN = {
    "increasing": "increasing",
    "decreasing": "decreasing",
    "inconclusive": "flat",
    "insufficient_data": "not estimable",
    "not_computed": "not computed",
}
_DIRECTION_AR = {
    "increasing": "\u0645\u062a\u0632\u0627\u064a\u062f",
    "decreasing": "\u0645\u062a\u0646\u0627\u0642\u0635",
    "inconclusive": "\u0645\u0633\u062a\u0642\u0631 \u062a\u0642\u0631\u064a\u0628\u064b\u0627",
    "insufficient_data": "\u063a\u064a\u0631 \u0642\u0627\u0628\u0644 \u0644\u0644\u062a\u0642\u062f\u064a\u0631",
    "not_computed": "\u0644\u0645 \u064a\u064f\u062d\u0633\u0628",
}


def _fmt(value: float | None, digits: int = 4) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}".rstrip("0").rstrip(".") if abs(value) < 1 else f"{value:.{digits}f}"


@dataclass(frozen=True)
class ExplanationSections:
    sections: list[tuple[str, str, str]]  # (section_id, title, body)
    actions: list[UiAction]
    limitations: list[str]


def build_explanation(result: ResultResponse, language: Language) -> ExplanationSections:
    """Render explanation text strictly from fields already in ``result``."""
    primary = result.variables[0]
    trend = primary.trend
    direction = trend.direction.value
    slope = _fmt(trend.slope_per_year)
    spatial = result.spatial
    cell_count = spatial.cell_count if spatial else 0
    missing_cells = spatial.missing_cell_count if spatial else 0
    period = f"{result.analysis.start_month} to {result.analysis.end_month}"
    region = result.analysis.region_display_name

    actions = [
        UiAction(
            action_id=UiActionId.FOCUS_REGION,
            label="Focus region" if language is Language.en else "\u062a\u0631\u0643\u064a\u0632 \u0639\u0644\u0649 \u0627\u0644\u0645\u0646\u0637\u0642\u0629",
            payload={"result_id": result.result_id, "region_id": result.analysis.region_id},
        ),
        UiAction(
            action_id=UiActionId.FOCUS_REGIONAL_CHART,
            label="Show regional chart" if language is Language.en else "\u0639\u0631\u0636 \u0627\u0644\u0631\u0633\u0645 \u0627\u0644\u0625\u0642\u0644\u064a\u0645\u064a",
            payload={"result_id": result.result_id, "variable_id": primary.variable_id},
        ),
        UiAction(
            action_id=UiActionId.REVEAL_CELLS,
            label="Reveal cells" if language is Language.en else "\u0625\u0638\u0647\u0627\u0631 \u0627\u0644\u062e\u0644\u0627\u064a\u0627",
            enabled=cell_count > 0,
            payload={"result_id": result.result_id, "spatial_url": spatial.spatial_url if spatial else None},
        ),
        UiAction(
            action_id=UiActionId.OPEN_SPIN_IT,
            label="Spin it" if language is Language.en else "\u062a\u062f\u0648\u064a\u0631 \u0627\u0644\u0641\u062a\u0631\u0629",
            payload={"result_id": result.result_id, "spin_endpoint": f"/v1/results/{result.result_id}/spin"},
        ),
        UiAction(
            action_id=UiActionId.OPEN_RECEIPT,
            label="Open receipt" if language is Language.en else "\u0641\u062a\u062d \u0627\u0644\u0625\u064a\u0635\u0627\u0644",
            payload={"receipt_id": result.receipt_id},
        ),
    ]

    if language is Language.ar:
        sections = [
            (
                "summary",
                "\u0627\u0644\u0645\u0644\u062e\u0635",
                (
                    f"\u0641\u064a \u0645\u0646\u0637\u0642\u0629 {region}\u060c \u0648\u062e\u0644\u0627\u0644 "
                    f"\u0627\u0644\u0641\u062a\u0631\u0629 {period}\u060c \u064a\u0638\u0647\u0631 "
                    f"{primary.display_name} \u0627\u062a\u062c\u0627\u0647\u064b\u0627 "
                    f"{_DIRECTION_AR[direction]} \u0628\u0645\u064a\u0644 "
                    f"{slope} {trend.slope_unit or ''} \u0633\u0646\u0648\u064a\u064b\u0627."
                ),
            ),
            (
                "interpretation",
                "\u0627\u0644\u062a\u0641\u0633\u064a\u0631",
                (
                    "\u0647\u0630\u0647 \u0627\u0644\u0642\u064a\u0645\u0629 \u0648\u0635\u0641\u064a\u0629 "
                    "\u0641\u0642\u0637: \u0644\u0645 \u064a\u064f\u062c\u0631\u0650 \u0627\u062e\u062a\u0628\u0627\u0631 "
                    "\u062f\u0644\u0627\u0644\u0629 \u0625\u062d\u0635\u0627\u0626\u064a\u0629\u060c \u0648\u0644\u0627 "
                    "\u064a\u0645\u0643\u0646 \u0627\u0633\u062a\u0646\u062a\u0627\u062c \u0639\u0644\u0627\u0642\u0629 "
                    "\u0633\u0628\u0628\u064a\u0629 \u0645\u0646 \u0627\u0644\u0627\u062a\u062c\u0627\u0647."
                ),
            ),
            (
                "spatial_insight",
                "\u0627\u0644\u0628\u0639\u062f \u0627\u0644\u0645\u0643\u0627\u0646\u064a",
                (
                    f"\u062a\u0645 \u062a\u0648\u0644\u064a\u062f {cell_count} \u062e\u0644\u064a\u0629 "
                    f"\u0634\u0628\u0643\u064a\u0629\u060c \u0648\u0645\u0646\u0647\u0627 {missing_cells} "
                    "\u0628\u062f\u0648\u0646 \u0628\u064a\u0627\u0646\u0627\u062a. \u0642\u062f "
                    "\u062a\u062e\u062a\u0644\u0641 \u0627\u0644\u062e\u0644\u0627\u064a\u0627 \u0639\u0646 "
                    "\u0627\u0644\u0645\u062a\u0648\u0633\u0637 \u0627\u0644\u0625\u0642\u0644\u064a\u0645\u064a."
                ),
            ),
            (
                "time_window_insight",
                "\u0646\u0627\u0641\u0630\u0629 \u0627\u0644\u0632\u0645\u0646",
                (
                    "\u064a\u0645\u0643\u0646 \u0627\u062e\u062a\u0628\u0627\u0631 \u062d\u0633\u0627\u0633\u064a\u0629 "
                    "\u0627\u0644\u0646\u062a\u064a\u062c\u0629 \u0644\u062a\u063a\u064a\u064a\u0631 \u0627\u0644\u0641\u062a\u0631\u0629 "
                    "\u0639\u0628\u0631 \u0645\u064a\u0632\u0629 \u00abSpin It\u00bb."
                ),
            ),
        ]
        limitations = [
            "\u0628\u064a\u0627\u0646\u0627\u062a \u0639\u0631\u0636 \u0627\u0635\u0637\u0646\u0627\u0639\u064a\u0629 \u0648\u0644\u064a\u0633\u062a \u0646\u062a\u064a\u062c\u0629 \u0639\u0644\u0645\u064a\u0629 \u0645\u0646 NASA.",
            "\u0644\u0645 \u064a\u062a\u0645 \u0627\u0633\u062a\u062e\u062f\u0627\u0645 \u0646\u0645\u0648\u0630\u062c \u0644\u063a\u0648\u064a \u0648\u0644\u0627 \u0646\u0638\u0627\u0645 \u0627\u0633\u062a\u0631\u062c\u0627\u0639.",
        ]
    else:
        sections = [
            (
                "summary",
                "Summary",
                (
                    f"For {region} between {period}, {primary.display_name} shows a "
                    f"descriptive {_DIRECTION_EN[direction]} slope of {slope} "
                    f"{trend.slope_unit or ''}."
                ),
            ),
            (
                "interpretation",
                "Interpretation",
                (
                    "The slope is descriptive only. No significance test was run, so this is "
                    "not evidence of a statistically confirmed trend, and no causal "
                    "relationship can be inferred from it."
                ),
            ),
            (
                "spatial_insight",
                "Spatial insight",
                (
                    f"The demo grid contains {cell_count} cells, of which {missing_cells} have "
                    "no data. Individual cells may differ from the regional average, which is "
                    "exactly what the map view is meant to expose."
                ),
            ),
            (
                "time_window_insight",
                "Time-window insight",
                (
                    "Use Spin It to see how the displayed trend changes when the time window "
                    "is shifted. Sign agreement across windows is descriptive, not a "
                    "probability that the trend is real."
                ),
            ),
        ]
        limitations = [
            "Synthetic demonstration data, not a NASA scientific result.",
            "No LLM or retrieval system was used; text is template-rendered.",
        ]

    return ExplanationSections(
        sections=[(section_id, title, body) for section_id, title, body in sections],
        actions=actions,
        limitations=limitations,
    )

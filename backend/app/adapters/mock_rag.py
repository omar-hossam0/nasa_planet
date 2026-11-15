"""Mock RAG adapter.

Delegates to the deterministic keyword/template engine. It is intentionally
thin: the only thing the AI team has to replace is this class.
"""

from __future__ import annotations

from app.mocks import ai as mock_ai
from app.schemas.common import Language
from app.schemas.results import ResultResponse


class MockRAGAdapter:
    """No model, no vector store, no retrieval. Deterministic output only."""

    provider_name = "mock_rules"

    def recommend(self, question: str, language: Language) -> mock_ai.RecommendationOutcome:
        return mock_ai.recommend(question, language)

    def explain(self, result: ResultResponse, language: Language) -> mock_ai.ExplanationSections:
        return mock_ai.build_explanation(result, language)

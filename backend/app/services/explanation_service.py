"""Template-rendered explanations for a completed result."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from app.adapters.interfaces import RAGAdapter
from app.core.exceptions import ResultNotCompleteError
from app.repositories.interfaces import JobRepository
from app.schemas.analysis import JobState
from app.schemas.explanation import (
    ExplanationRequest,
    ExplanationResponse,
    ExplanationSection,
)
from app.services.result_service import ResultService


class ExplanationService:
    def __init__(
        self,
        *,
        results: ResultService,
        jobs: JobRepository,
        rag: RAGAdapter,
    ) -> None:
        self._results = results
        self._jobs = jobs
        self._rag = rag

    def explain(self, request: ExplanationRequest) -> ExplanationResponse:
        result = self._results.get_result(request.result_id)

        job = self._jobs.get(result.job_id)
        if job is None or job.status is not JobState.completed:
            raise ResultNotCompleteError(result.job_id, job.status.value if job else "unknown")

        rendered = self._rag.explain(result, request.language)

        explanation_id = "expl_mock_" + hashlib.sha256(
            f"{result.result_id}:{request.language.value}".encode("utf-8")
        ).hexdigest()[:8]

        return ExplanationResponse(
            explanation_id=explanation_id,
            result_id=result.result_id,
            language=request.language,
            sections=[
                ExplanationSection(section_id=section_id, title=title, body=body)
                for section_id, title, body in rendered.sections
            ],
            actions=rendered.actions,
            references=[],
            limitations=rendered.limitations,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

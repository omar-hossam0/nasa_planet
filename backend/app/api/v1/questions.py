"""Grounded concept questions, independent of analysis-session mutable state."""
from functools import lru_cache
from pathlib import Path
import sys

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from app.core.dependencies import Container, get_container
from app.core.exceptions import RegionNotFoundError
from typing import Literal
from app.schemas.common import MonthStr
from app.services.question_workflow import plan_question
import re
from packages.rag.grounded_definitions import definition_answer

router = APIRouter(tags=['explanations'])


class QuestionRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    query: str = Field(min_length=1, max_length=500)
    region_id: str | None = Field(default=None, max_length=128)
    data_revision: str | None = Field(default=None, max_length=128)
    language: Literal['en', 'ar'] = 'en'
    start_month: MonthStr | None = None
    end_month: MonthStr | None = None


@lru_cache(maxsize=1)
def get_pipeline():
    root = str(Path(__file__).resolve().parents[4])
    if root not in sys.path:
        sys.path.insert(0, root)
    from packages.rag.explanation import ExplanationPipeline
    from packages.rag.provider import GeminiClient
    from app.core.config import get_settings
    settings = get_settings()
    provider = GeminiClient(provider=settings.llm_provider,
        api_key=settings.gemini_api_key.get_secret_value(), model=settings.llm_model,
        timeout=settings.llm_timeout_seconds, max_retries=settings.llm_max_retries)
    return ExplanationPipeline(provider=provider)


@router.post('/explanations/ask')
def ask(payload: QuestionRequest, container: Container = Depends(get_container)):
    if not container.settings.rag_enabled:
        raise HTTPException(503, 'RAG is disabled; configure RAG_ENABLED=true')
    if not payload.query.strip():
        raise HTTPException(422, 'Question must contain text')
    region_id = None
    if payload.region_id:
        region_id = container.data.resolve_region_id(payload.region_id)
        if not region_id:
            raise RegionNotFoundError(payload.region_id)
    workflow = plan_question(payload.query, container.data, container.catalog, region_id,
                            payload.start_month, payload.end_month, payload.language)
    region_id = workflow['region_id']
    result = get_pipeline().explain(payload.query, region_id=region_id,
                                    data_revision=payload.data_revision)
    result['workflow'] = workflow
    definition = bool(re.search(r'what\s+(?:is|are|does)|define|meaning|ما هو|ما هي|يعني|معنى|معني|تعريف', payload.query, re.I))
    if definition:
        workflow['analysis_request'] = None
        workflow['state'] = 'documentation_only'
        workflow['message'] = 'Definition and source limitations.' if payload.language=='en' else 'تعريف المتغير وحدود مصدره.'
        ids = result.get('variable_ids', [])
        if not result.get('answer') and len(ids)==1 and result.get('citations') and result.get('status') not in ('unsupported','unavailable','ambiguous'):
            result['answer'] = definition_answer(ids[0], payload.language)
            result['mode'] = 'grounded_template'
    # Local retrieval returns evidence, not a generated answer. Keep this distinction
    # explicit and never manufacture a conversational response from unavailable data.
    result['answer'] = result.get('answer')
    result['capability_note'] = (
        'Explains project documentation. Does not read your analysis results or calculate regional statistics. Each question is independent.'
        if payload.language == 'en' else
        'يشرح وثائق المشروع. لا يقرأ نتائج تحليلك ولا يحسب إحصائيات المنطقة. كل سؤال مستقل.')
    result['region_id'] = region_id
    return result

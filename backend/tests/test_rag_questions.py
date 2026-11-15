import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.api.v1 import questions
from tests.conftest import make_settings


@pytest.fixture
def rag_client(monkeypatch):
    questions.get_pipeline()  # configure the same repository import path as runtime
    from packages.rag.explanation import ExplanationPipeline
    from packages.rag.provider import GeminiClient
    pipeline = ExplanationPipeline(provider=GeminiClient(api_key=''))
    monkeypatch.setattr(questions, 'get_pipeline', lambda: pipeline)
    with TestClient(create_app(make_settings(rag_enabled=True))) as client:
        yield client, pipeline


@pytest.mark.parametrize('query,variable', [
    ('What is precipitation?', 'precipitation'),
    ('ما هو الهطول؟', 'precipitation'),
    ('ما هو NDVI؟', 'vegetation_greenness'),
    ('What is soil moisture?', 'soil_moisture'),
])
def test_retrieval_has_exact_corpus_evidence(rag_client, query, variable):
    client, pipeline = rag_client
    response = client.post('/v1/explanations/ask', json={'query': query, 'language': 'ar'})
    assert response.status_code == 200
    result = response.json()
    assert result['mode'] == 'local_retrieval'
    assert result['answer'] is None
    assert variable in result['variable_ids']
    assert result['citations']
    corpus = {chunk['chunk_id']: chunk for chunk in pipeline.retriever.chunks}
    from packages.rag.retriever import PRODUCT_OF_SOURCE
    for citation in result['citations']:
        chunk = corpus[citation['chunk_id']]
        assert PRODUCT_OF_SOURCE[citation['source_id']] == variable
        assert citation['text'] == chunk['text']
        assert citation['source_url'] == chunk['source_url']
        assert citation['raw_source_hash'] == chunk['raw_source_hash']


def test_unsupported_question_does_not_invent_an_answer(rag_client):
    client, _ = rag_client
    result = client.post('/v1/explanations/ask', json={'query': 'Who won the football match?'}).json()
    assert result['status'] == 'unsupported'
    assert not result['answer']
    assert not result['citations']


def test_invalid_region_and_empty_question_are_rejected(rag_client):
    client, _ = rag_client
    assert client.post('/v1/explanations/ask', json={'query': 'What is NDVI?', 'region_id': 'unknown'}).status_code == 404
    assert client.post('/v1/explanations/ask', json={'query': '   '}).status_code == 422


def test_disabled_rag_returns_service_error():
    with TestClient(create_app(make_settings(rag_enabled=False))) as client:
        assert client.post('/v1/explanations/ask', json={'query': 'What is NDVI?'}).status_code == 503


@pytest.mark.parametrize('query,language', [('ما هو NDVI؟', 'Arabic'), ('What is NDVI?', 'English')])
def test_prompt_requests_the_question_language(rag_client, query, language):
    _, pipeline = rag_client
    from packages.rag.explanation import build_evidence_context, build_prompt
    local = pipeline.retriever.answer_query(query)
    prompt = build_prompt(build_evidence_context(pipeline.retriever, query, local))
    assert f'Write the answer in {language}' in prompt

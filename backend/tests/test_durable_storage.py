from fastapi.testclient import TestClient
import pytest
from app.main import create_app
from app.core.config import Settings
from tests.conftest import BASE_ANALYSIS, make_settings


def test_queue_survives_api_restart_and_worker_persists_results(tmp_path):
    settings = make_settings(database_url=f'sqlite:///{tmp_path / "backend.db"}',
                             database_auto_create=True, job_backend='database')
    first = create_app(settings)
    with TestClient(first) as client:
        response = client.post('/v1/analyses', json=BASE_ANALYSIS)
        assert response.status_code == 202
        job_id = response.json()['job_id']
        assert response.json()['status'] == 'queued'
    second = create_app(settings)
    container = second.state.container
    assert container.job_manager.run_one(container)
    assert not container.job_manager.run_one(container)
    with TestClient(second) as client:
        job = client.get(f'/v1/analyses/{job_id}').json()
        assert job['status'] == 'completed'
        result = client.get(f'/v1/results/{job["result_id"]}').json()
        assert client.get(f'/v1/receipts/{result["receipt_id"]}').status_code == 200
        cached = client.post('/v1/analyses', json=BASE_ANALYSIS)
        assert cached.status_code == 200
        assert cached.json()['cached']
        assert cached.json()['job_id'] == job_id
    first.state.container.database.engine.dispose()
    container.database.engine.dispose()


def test_transaction_rolls_back_partial_receipt_bundle(tmp_path):
    from app.repositories.sql import Database, repositories
    from app.repositories.interfaces import CacheEntry
    db = Database(f'sqlite:///{tmp_path / "rollback.db"}')
    db.initialize()
    cache = repositories(db)[4]
    with pytest.raises(RuntimeError):
        with db.transaction():
            cache.put(CacheEntry('key', 'job', 'result', 'receipt'))
            raise RuntimeError('simulated write failure')
    assert cache.get('key') is None
    db.engine.dispose()


def test_production_cannot_silently_serve_mock_science():
    with pytest.raises(ValueError, match='Production release'):
        Settings(app_env='production')


def test_real_rag_endpoint_can_retrieve_without_provider_key(monkeypatch):
    from app.api.v1.questions import get_pipeline
    monkeypatch.setenv('GEMINI_API_KEY', '')
    from app.core.config import get_settings
    get_settings.cache_clear()
    get_pipeline.cache_clear()
    with TestClient(create_app(make_settings(rag_enabled=True))) as client:
        result = client.post('/v1/explanations/ask', json={'query': 'What is precipitation?'})
        assert result.status_code == 200
        assert result.json()['mode'] == 'local_retrieval'
        assert result.json()['citations']
    get_pipeline.cache_clear()


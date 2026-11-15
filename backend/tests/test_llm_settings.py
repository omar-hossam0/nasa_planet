from app.core.config import Settings, get_settings
from app.api.v1.questions import get_pipeline


def test_dotenv_provider_settings_are_loaded_and_secret_is_hidden(tmp_path, monkeypatch):
    file = tmp_path / '.env'
    file.write_text('LLM_PROVIDER=gemini\nGEMINI_API_KEY=test-secret-only\nLLM_MODEL=gemini-2.5-flash\nLLM_TIMEOUT_SECONDS=8\n', encoding='utf-8')
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    settings = Settings(_env_file=file)
    assert settings.gemini_api_key.get_secret_value() == 'test-secret-only'
    assert 'test-secret-only' not in repr(settings)
    assert 'test-secret-only' not in settings.model_dump_json()
    assert settings.llm_timeout_seconds == 8


def test_pipeline_uses_server_settings_without_provider_network_call(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'test-provider-key')
    monkeypatch.setenv('LLM_TIMEOUT_SECONDS', '6')
    get_settings.cache_clear()
    get_pipeline.cache_clear()
    try:
        pipeline = get_pipeline()
        assert pipeline.provider.api_key == 'test-provider-key'
        assert pipeline.provider.timeout == 6
        assert pipeline.provider.is_configured()
    finally:
        get_pipeline.cache_clear()
        get_settings.cache_clear()

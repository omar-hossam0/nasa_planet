import json
import os
import socket
import urllib.error
import urllib.request

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

DEFAULT_PROVIDER = "gemini"
DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_TIMEOUT_SECONDS = 8
DEFAULT_MAX_RETRIES = 1

REASON_NOT_CONFIGURED = "provider_not_configured"
REASON_MISSING_KEY = "missing_api_key"
REASON_NETWORK = "network_error"
REASON_TIMEOUT = "timeout"
REASON_HTTP = "http_error"
REASON_EMPTY = "empty_response"


class ProviderError(Exception):
    def __init__(self, reason, detail=None):
        self.reason = reason
        self.detail = detail
        super().__init__(detail or reason)


def _env_float(name, default):
    try:
        return float(os.environ.get(name) or default)
    except (TypeError, ValueError):
        return default


def _env_int(name, default):
    try:
        return int(os.environ.get(name) or default)
    except (TypeError, ValueError):
        return default


class GeminiClient:
    def __init__(self, provider=None, api_key=None, model=None, timeout=None, max_retries=None):
        self.provider = (provider or os.environ.get("LLM_PROVIDER") or DEFAULT_PROVIDER).strip().lower()
        self.api_key = api_key if api_key is not None else os.environ.get("GEMINI_API_KEY") or ""
        self.model = model or os.environ.get("LLM_MODEL") or DEFAULT_MODEL
        self.timeout = timeout if timeout is not None else _env_float("LLM_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)
        self.max_retries = (
            max_retries if max_retries is not None else _env_int("LLM_MAX_RETRIES", DEFAULT_MAX_RETRIES)
        )

    def is_configured(self):
        return self.provider == DEFAULT_PROVIDER and bool(self.api_key.strip())

    def generate(self, prompt):
        if self.provider != DEFAULT_PROVIDER:
            raise ProviderError(REASON_NOT_CONFIGURED, f"unsupported provider {self.provider!r}")
        if not self.api_key.strip():
            raise ProviderError(
                REASON_MISSING_KEY,
                "GEMINI_API_KEY is not set; keyless runs use the deterministic local_retrieval mode",
            )
        body = json.dumps(
            {
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.2,
                    "maxOutputTokens": 2048,
                    "responseMimeType": "application/json",
                },
            }
        ).encode("utf-8")
        url = f"{GEMINI_API_BASE}/{self.model}:generateContent"
        request = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key.strip(),
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            raise ProviderError(REASON_HTTP, f"gemini HTTP {exc.code}") from None
        except (socket.timeout, TimeoutError):
            raise ProviderError(REASON_TIMEOUT, f"gemini request timed out after {self.timeout}s") from None
        except (urllib.error.URLError, OSError):
            raise ProviderError(REASON_NETWORK, "gemini endpoint was unreachable") from None
        return _extract_text(raw)


def _extract_text(raw):
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ProviderError(REASON_EMPTY, "gemini response body was not valid JSON") from None
    try:
        parts = data["candidates"][0]["content"]["parts"]
        text = "".join(part.get("text", "") for part in parts)
    except (KeyError, IndexError, TypeError):
        raise ProviderError(REASON_EMPTY, "gemini response contained no candidate text") from None
    if not text.strip():
        raise ProviderError(REASON_EMPTY, "gemini returned an empty response")
    return text

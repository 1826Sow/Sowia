"""Regression tests for provider-specific AI configuration."""
import importlib

import config
import settings


def _reload_with_settings(monkeypatch, values):
    # Isolate configuration loading from the developer's real environment/secrets.
    with monkeypatch.context() as patch:
        patch.setattr(
            settings,
            "get_setting",
            lambda name, default="": values.get(name, default),
        )
        loaded = importlib.reload(config)
        snapshot = {
            "API_KEY": loaded.API_KEY,
            "MODEL": loaded.MODEL,
            "BASE_URL": loaded.BASE_URL,
            "USING_GROQ": loaded.USING_GROQ,
        }
    # Restore the module to the normal settings reader for other tests.
    importlib.reload(config)
    return snapshot


def test_groq_ignores_stale_openai_base_url(monkeypatch):
    result = _reload_with_settings(
        monkeypatch,
        {
            "GROQ_API_KEY": "groq-test-key",
            "OPENAI_API_KEY": "old-openai-key",
            "OPENAI_BASE_URL": "https://old-openai-endpoint.example/v1",
        },
    )

    assert result["API_KEY"] == "groq-test-key"
    assert result["USING_GROQ"] is True
    assert result["BASE_URL"] == "https://api.groq.com/openai/v1"
    assert result["MODEL"] == "openai/gpt-oss-20b"


def test_groq_accepts_its_own_optional_base_url(monkeypatch):
    result = _reload_with_settings(
        monkeypatch,
        {
            "GROQ_API_KEY": "groq-test-key",
            "GROQ_BASE_URL": "https://custom-groq-endpoint.example/v1",
            "OPENAI_BASE_URL": "https://old-openai-endpoint.example/v1",
        },
    )

    assert result["BASE_URL"] == "https://custom-groq-endpoint.example/v1"


def test_openai_keeps_its_existing_base_url_setting(monkeypatch):
    result = _reload_with_settings(
        monkeypatch,
        {
            "OPENAI_API_KEY": "openai-test-key",
            "OPENAI_BASE_URL": "https://openai-compatible.example/v1",
        },
    )

    assert result["API_KEY"] == "openai-test-key"
    assert result["USING_GROQ"] is False
    assert result["BASE_URL"] == "https://openai-compatible.example/v1"

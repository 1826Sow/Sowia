"""Tests for safe assistant-provider error handling."""
import httpx
import pytest
import openai

import assistant


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (
            openai.APIConnectionError(
                message="private network detail",
                request=httpx.Request("POST", "https://api.example.test"),
            ),
            "ne parvient pas à joindre",
        ),
        (
            openai.APITimeoutError(
                request=httpx.Request("POST", "https://api.example.test"),
            ),
            "trop de temps",
        ),
        (
            openai.APIStatusError(
                message="private provider detail",
                response=httpx.Response(
                    503,
                    request=httpx.Request("POST", "https://api.example.test"),
                ),
                body=None,
            ),
            "problème temporaire",
        ),
    ],
)
def test_answer_translates_provider_errors_without_leaking_details(
    monkeypatch, error, message
):
    monkeypatch.setattr(assistant, "API_KEY", "test-key")

    class FakeCompletions:
        def create(self, **kwargs):
            raise error

    class FakeClient:
        def __init__(self, **kwargs):
            self.chat = type("Chat", (), {"completions": FakeCompletions()})()

    monkeypatch.setattr(assistant, "OpenAI", FakeClient)

    with pytest.raises(RuntimeError, match=message) as raised:
        assistant.answer([{"role": "user", "content": "Bonjour"}])

    assert "private" not in str(raised.value)


def test_answer_reports_missing_api_key_without_calling_provider(monkeypatch):
    monkeypatch.setattr(assistant, "API_KEY", "")

    def unexpected_client(**kwargs):
        pytest.fail("The provider must not be called without an API key.")

    monkeypatch.setattr(assistant, "OpenAI", unexpected_client)

    with pytest.raises(RuntimeError, match="Aucune clé API IA"):
        assistant.answer([{"role": "user", "content": "Bonjour"}])



def test_groq_rate_limit_falls_back_to_openai_when_both_keys_are_configured(monkeypatch):
    monkeypatch.setattr(assistant, "API_KEY", "groq-key")
    monkeypatch.setattr(assistant, "BASE_URL", "https://api.groq.com/openai/v1")
    monkeypatch.setattr(assistant, "MODEL", "openai/gpt-oss-20b")
    monkeypatch.setattr(assistant, "GROQ_API_KEY", "groq-key")
    monkeypatch.setattr(assistant, "OPENAI_API_KEY", "openai-key")
    monkeypatch.setattr(assistant, "OPENAI_BASE_URL", None)
    monkeypatch.setattr(assistant, "OPENAI_MODEL", "gpt-4o-mini")
    calls = []

    class FakeCompletions:
        def __init__(self, provider):
            self.provider = provider

        def create(self, **kwargs):
            calls.append((self.provider, kwargs["model"]))
            if self.provider == "groq-key":
                request = httpx.Request("POST", "https://api.groq.com")
                response = httpx.Response(429, request=request)
                raise openai.RateLimitError("throttled", response=response, body=None)
            return type("Response", (), {"choices": [type("Choice", (), {"message": type("Message", (), {"content": "Réponse de secours"})()})()]})()

    class FakeClient:
        def __init__(self, api_key, base_url=None):
            self.chat = type("Chat", (), {"completions": FakeCompletions(api_key)})()

    monkeypatch.setattr(assistant, "OpenAI", FakeClient)
    result = assistant.answer([{"role": "user", "content": "Bonjour"}])

    assert result == "Réponse de secours"
    assert calls == [("groq-key", "openai/gpt-oss-20b"), ("openai-key", "gpt-4o-mini")]

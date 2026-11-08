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

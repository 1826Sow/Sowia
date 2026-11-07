from types import SimpleNamespace

import pytest

import assistant


def _fake_client(content):
    return SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=lambda **kwargs: SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            message=SimpleNamespace(content=content)
                        )
                    ]
                )
            )
        )
    )


def test_answer_returns_provider_content(monkeypatch):
    captured = {}

    def fake_openai(**kwargs):
        captured.update(kwargs)
        return _fake_client("Bonjour, je suis SOW IA.")

    monkeypatch.setattr(assistant, "API_KEY", "test-key")
    monkeypatch.setattr(assistant, "BASE_URL", "https://example.test/v1")
    monkeypatch.setattr(assistant, "MODEL", "test-model")
    monkeypatch.setattr(assistant, "OpenAI", fake_openai)

    result = assistant.answer([{"role": "user", "content": "Bonjour"}])

    assert result == "Bonjour, je suis SOW IA."
    assert captured["timeout"] == 45.0


@pytest.mark.parametrize("content", [None, "", "   "])
def test_answer_rejects_empty_provider_content(monkeypatch, content):
    monkeypatch.setattr(assistant, "API_KEY", "test-key")
    monkeypatch.setattr(assistant, "BASE_URL", None)
    monkeypatch.setattr(assistant, "MODEL", "test-model")
    monkeypatch.setattr(assistant, "OpenAI", lambda **kwargs: _fake_client(content))

    with pytest.raises(RuntimeError, match="sans contenu"):
        assistant.answer([{"role": "user", "content": "Bonjour"}])


def test_answer_explains_missing_api_key_without_network(monkeypatch):
    monkeypatch.setattr(assistant, "API_KEY", "")

    with pytest.raises(RuntimeError, match="Aucune clé API IA"):
        assistant.answer([{"role": "user", "content": "Bonjour"}])


def test_answer_rejects_provider_response_without_choices(monkeypatch):
    monkeypatch.setattr(assistant, "API_KEY", "test-key")
    monkeypatch.setattr(assistant, "BASE_URL", None)
    monkeypatch.setattr(assistant, "MODEL", "test-model")
    monkeypatch.setattr(
        assistant,
        "OpenAI",
        lambda **kwargs: SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(
                    create=lambda **call_kwargs: SimpleNamespace(choices=[])
                )
            )
        ),
    )

    with pytest.raises(RuntimeError, match="aucun choix de réponse"):
        assistant.answer([{"role": "user", "content": "Bonjour"}])

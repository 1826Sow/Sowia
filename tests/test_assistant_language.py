"""Tests that assistant replies follow the selected interface language."""
import pytest

from assistant import _offline_reply, build_system_prompt


@pytest.mark.parametrize(
    ("language", "required_instruction"),
    [
        ("Français", "Réponds toujours en français."),
        ("English", "Always respond in English."),
        ("Español", "Responde siempre en español."),
        ("中文", "始终使用简体中文回答。"),
        ("Deutsch", "Antworte immer auf Deutsch."),
        ("العربية", "أجب دائمًا باللغة العربية الفصحى."),
    ],
)
def test_system_prompt_enforces_selected_response_language(language, required_instruction):
    prompt = build_system_prompt(language=language)

    assert required_instruction in prompt
    assert "RESPONSE LANGUAGE — MANDATORY" in prompt


@pytest.mark.parametrize(
    ("language", "expected_phrase"),
    [
        ("Français", "Le mode de secours de SOW IA"),
        ("English", "SOW IA is in fallback mode"),
        ("Español", "SOW IA está en modo de respaldo"),
        ("中文", "SOW IA 当前处于备用模式"),
        ("Deutsch", "SOW IA befindet sich im Ersatzmodus"),
        ("العربية", "يعمل SOW IA حاليًا في الوضع الاحتياطي"),
    ],
)
def test_offline_reply_uses_selected_language(language, expected_phrase):
    reply = _offline_reply([{"role": "user", "content": "Hello"}], language=language)

    assert reply.startswith(expected_phrase)


def test_unknown_language_uses_french_as_safe_default():
    reply = _offline_reply([], language="unsupported")

    assert reply.startswith("Le mode de secours de SOW IA")

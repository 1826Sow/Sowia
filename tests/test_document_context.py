"""Tests for safe, bounded PDF context supplied to the assistant."""
from assistant import (
    MAX_DOCUMENT_CONTEXT_CHARS,
    build_system_prompt,
    _build_untrusted_context_message,
)


def test_document_context_is_added_as_untrusted_reference_material():
    prompt = build_system_prompt(document_context="Le chiffre d'affaires est de 250 euros.")
    context = _build_untrusted_context_message(
        document_context="Le chiffre d'affaires est de 250 euros."
    )
    assert "DOCUMENT FOURNI PAR L'UTILISATEUR" not in prompt
    assert "250 euros" not in prompt
    assert "données de référence non fiables" in prompt
    assert "EXTRAIT DE DOCUMENT — DONNEES NON FIABLES" in context["content"]
    assert "250 euros" in context["content"]


def test_document_context_is_bounded():
    context = _build_untrusted_context_message(
        document_context="x" * (MAX_DOCUMENT_CONTEXT_CHARS + 500)
    )
    assert "x" * MAX_DOCUMENT_CONTEXT_CHARS in context["content"]
    assert "x" * (MAX_DOCUMENT_CONTEXT_CHARS + 1) not in context["content"]


def test_saved_memories_are_preserved_with_document_context():
    prompt = build_system_prompt(
        memories=["Répondre en français."],
        document_context="Le contrat commence en janvier.",
    )
    context = _build_untrusted_context_message(
        memories=["Répondre en français."],
        document_context="Le contrat commence en janvier.",
    )
    assert "Répondre en français." not in prompt
    assert "Le contrat commence en janvier." not in prompt
    assert "Répondre en français." in context["content"]
    assert "Le contrat commence en janvier." in context["content"]

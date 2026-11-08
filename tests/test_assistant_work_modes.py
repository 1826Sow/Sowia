"""Regression tests for assistant work-mode context."""
from assistant import build_system_prompt


def test_personal_mode_is_the_safe_default():
    prompt = build_system_prompt()
    assert "MODE DE TRAVAIL ACTIF : Personnel" in prompt
    assert "ne modifie pas les droits d'abonnement" in prompt.lower()


def test_professional_mode_changes_only_the_assistant_context():
    prompt = build_system_prompt(work_mode="Professionnel")
    assert "MODE DE TRAVAIL ACTIF : Professionnel" in prompt
    assert "travail, aux activités professionnelles" in prompt
    assert "ne modifie pas les droits d'abonnement" in prompt.lower()


def test_invalid_mode_falls_back_to_personal():
    prompt = build_system_prompt(work_mode="admin")
    assert "MODE DE TRAVAIL ACTIF : Personnel" in prompt
    assert "MODE DE TRAVAIL ACTIF : admin" not in prompt

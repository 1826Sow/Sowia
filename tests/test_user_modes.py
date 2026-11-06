"""Tests for SOW IA work-mode selection and prompt context."""
import pytest

from user_modes import MODE_OPTIONS, mode_system_instruction, normalize_user_mode
from assistant import build_system_prompt


@pytest.mark.parametrize("mode", ["Personnel", "Professionnel"])
def test_supported_modes_are_preserved(mode):
    assert normalize_user_mode(mode) == mode
    assert mode in mode_system_instruction(mode)


@pytest.mark.parametrize("value", [None, "", "premium", "Admin", 42, []])
def test_unknown_mode_falls_back_to_personnel(value):
    assert normalize_user_mode(value) == "Personnel"
    assert "MODE DE TRAVAIL ACTIF : Personnel" in mode_system_instruction(value)


def test_modes_are_contexts_not_subscription_entitlements():
    assert set(MODE_OPTIONS) == {"Personnel", "Professionnel"}
    assert "abonnement" in mode_system_instruction("Professionnel").lower()


def test_assistant_system_prompt_includes_selected_mode():
    personal = build_system_prompt(user_mode="Personnel")
    professional = build_system_prompt(user_mode="Professionnel")
    assert "MODE DE TRAVAIL ACTIF : Personnel" in personal
    assert "MODE DE TRAVAIL ACTIF : Professionnel" in professional
    assert personal != professional

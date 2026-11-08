"""Tests for safe Personnel / Professionnel assistant modes."""
from user_modes import MODE_OPTIONS, mode_system_instruction, normalize_user_mode


def test_supported_modes_are_explicit():
    assert tuple(MODE_OPTIONS) == ("Personnel", "Professionnel")


def test_invalid_mode_falls_back_to_personnel():
    assert normalize_user_mode("admin") == "Personnel"
    assert normalize_user_mode(None) == "Personnel"


def test_professional_mode_changes_context_without_granting_access():
    instruction = mode_system_instruction("Professionnel")
    assert "MODE DE TRAVAIL ACTIF : Professionnel" in instruction
    assert "ne modifie pas les droits d'abonnement" in instruction.lower()


def test_personal_mode_has_personal_context():
    assert "MODE DE TRAVAIL ACTIF : Personnel" in mode_system_instruction("Personnel")

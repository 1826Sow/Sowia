"""Tests for Personnel and Professionnel workspace navigation."""
from workspace_access import (
    WORKSPACE_MODES,
    normalize_workspace_mode,
    workspace_home_content,
    workspace_navigation,
)


def test_workspace_modes_are_explicit():
    assert WORKSPACE_MODES == ("Personnel", "Professionnel")


def test_invalid_workspace_defaults_to_personnel():
    assert normalize_workspace_mode("unknown") == "Personnel"


def test_professional_navigation_hides_personal_memory_only():
    pages = workspace_navigation("Professionnel")
    assert "Ma mémoire" not in pages
    assert "Assistant IA" in pages
    assert "Créer un PDF" in pages
    assert "Mes documents" in pages


def test_personal_navigation_keeps_memory():
    assert "Ma mémoire" in workspace_navigation("Personnel")


def test_professional_home_discloses_premium_lock_without_active_entitlement():
    home = workspace_home_content("Professionnel", premium_active=False)
    assert home["title"] == "Votre espace Professionnel"
    assert "reste verrouillé" in home["notice"]
    assert any(item[1] == "Mes documents" for item in home["shortcuts"])


def test_professional_home_does_not_show_lock_notice_when_premium_is_active():
    home = workspace_home_content("Professionnel", premium_active=True)
    assert home["notice"] == ""


def test_personal_home_keeps_memory_shortcut():
    home = workspace_home_content("Personnel")
    assert any(item[1] == "Ma mémoire" for item in home["shortcuts"])

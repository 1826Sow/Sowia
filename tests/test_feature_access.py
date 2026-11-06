"""Tests for workspace selection and server-side Premium feature guards."""

import feature_access as access


def test_workspace_mode_defaults_to_personnel_for_unknown_values():
    assert access.normalize_workspace_mode(None) == "Personnel"
    assert access.normalize_workspace_mode("unexpected") == "Personnel"


def test_workspace_modes_are_explicit_and_supported():
    assert access.WORKSPACE_MODES == ("Personnel", "Professionnel")
    assert access.normalize_workspace_mode("Professionnel") == "Professionnel"


def test_premium_feature_is_denied_without_active_server_entitlement():
    assert not access.can_access_feature("Mes documents", None)
    assert not access.can_access_feature("Mes documents", {"status": "inactive"})
    assert not access.can_access_feature("Mes documents", {"status": "cancelled"})


def test_premium_feature_is_allowed_only_with_active_entitlement():
    assert access.can_access_feature("Mes documents", {"status": "active"})


def test_known_free_features_remain_available_without_premium():
    assert access.can_access_feature("Assistant IA", None)
    assert access.can_access_feature("Analyse PDF", {"status": "inactive"})


def test_unknown_features_are_denied_until_registered():
    assert not access.can_access_feature("Future Premium Feature", {"status": "active"})
    assert not access.can_access_feature("Typo in feature name", None)


def test_personal_home_keeps_personal_tools_and_copy():
    home = access.workspace_home_content("Personnel", premium_active=False)
    assert home["title"] == "Bienvenue sur SOW IA"
    assert "Ma mémoire" in [item[1] for item in home["shortcuts"]]
    assert home["notice"] == ""


def test_professional_home_has_work_context_and_premium_notice():
    home = access.workspace_home_content("Professionnel", premium_active=False)
    assert home["title"] == "Votre espace Professionnel"
    assert "Ma mémoire" not in [item[1] for item in home["shortcuts"]]
    assert "Premium" in home["notice"]
    assert "documents professionnels" in home["description"]


def test_professional_home_notice_disappears_only_with_active_premium():
    home = access.workspace_home_content("Professionnel", premium_active=True)
    assert home["notice"] == ""
    assert "Mes documents" in [item[1] for item in home["shortcuts"]]


def test_professional_navigation_hides_personal_memory_page():
    pages = access.workspace_navigation("Professionnel")
    assert "Ma mémoire" not in pages
    assert "Assistant IA" in pages
    assert "Mes documents" in pages


def test_personal_navigation_keeps_personal_memory_page():
    pages = access.workspace_navigation("Personnel")
    assert "Ma mémoire" in pages
    assert pages == access.NAVIGATION_PAGES


def test_unknown_workspace_uses_safe_personal_navigation():
    assert access.workspace_navigation("unknown") == access.workspace_navigation("Personnel")

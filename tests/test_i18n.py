import pytest

from i18n import LANGUAGES, translate


@pytest.mark.parametrize("language", LANGUAGES)
def test_language_selection_has_a_label_for_each_supported_language(language):
    assert isinstance(translate("Accueil", language), str)
    assert translate("Accueil", language)


def test_french_is_the_default_and_unknown_language_falls_back_to_french():
    assert translate("Accueil") == "Accueil"
    assert translate("Accueil", "Klingon") == "Accueil"


def test_english_navigation_and_workspace_labels_are_translated():
    assert translate("Développement mondial", "English") == "Global growth"
    assert translate("Professionnel", "English") == "Professional"


def test_english_home_and_common_controls_are_translated():
    assert translate("Bienvenue dans SOW IA", "English") == "Welcome to SOW IA"
    assert translate("Espace de travail", "English") == "Workspace"
    assert translate("VALIDER", "English") == "CONTINUE"
    assert translate("🔐 Espaces de travail sécurisés", "English") == "🔐 Secure workspaces"


def test_english_home_hero_is_translated():
    source = "La technologie au service des décisions, de la productivité et des opportunités. Un environnement conçu pour accompagner les particuliers, les entreprises et les partenaires dans leur développement."
    assert translate(source, "English").startswith("Technology for better decisions")

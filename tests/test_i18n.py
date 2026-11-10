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

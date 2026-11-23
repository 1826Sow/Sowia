import pytest

from i18n import translate


@pytest.mark.parametrize(
    "language,expected",
    [
        ("English", "Standard search"),
        ("Español", "Búsqueda estándar"),
        ("中文", "常规搜索"),
        ("Deutsch", "Standardsuche"),
        ("العربية", "بحث عادي"),
    ],
)
def test_web_search_tab_is_localized(language, expected, monkeypatch):
    monkeypatch.setattr("i18n._translate_missing_interface_copy", lambda text, selected: text)
    assert translate("Recherche classique", language) == expected


@pytest.mark.parametrize(
    "language,expected",
    [
        ("English", "Fact-check information"),
        ("Español", "Verificar una información"),
        ("中文", "核实信息"),
        ("Deutsch", "Information überprüfen"),
        ("العربية", "التحقق من معلومة"),
    ],
)
def test_information_verification_tab_is_localized(language, expected, monkeypatch):
    monkeypatch.setattr("i18n._translate_missing_interface_copy", lambda text, selected: text)
    assert translate("Vérifier une information", language) == expected


@pytest.mark.parametrize(
    "language,expected",
    [
        ("English", "What would you like to search for?"),
        ("Español", "¿Qué desea buscar?"),
        ("中文", "您想搜索什么？"),
        ("Deutsch", "Wonach möchten Sie suchen?"),
        ("العربية", "ما الذي تريد البحث عنه؟"),
    ],
)
def test_web_search_input_prompt_is_localized(language, expected, monkeypatch):
    monkeypatch.setattr("i18n._translate_missing_interface_copy", lambda text, selected: text)
    assert translate("Que souhaitez-vous rechercher ?", language) == expected


@pytest.mark.parametrize(
    "language,expected",
    [
        ("English", "What claim would you like to verify?"),
        ("Español", "¿Qué afirmación desea verificar?"),
        ("中文", "您想核实哪项说法？"),
        ("Deutsch", "Welche Aussage möchten Sie überprüfen?"),
        ("العربية", "ما الادعاء الذي تريد التحقق منه؟"),
    ],
)
def test_fact_check_prompt_is_localized(language, expected, monkeypatch):
    monkeypatch.setattr("i18n._translate_missing_interface_copy", lambda text, selected: text)
    assert translate("Quelle affirmation souhaitez-vous vérifier ?", language) == expected

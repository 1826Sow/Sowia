from pathlib import Path

from i18n import LANGUAGES, translate


def test_post_login_homepage_copy_is_translated_in_all_six_languages():
    keys = (
        "PLATEFORME INTELLIGENTE · VISION INTERNATIONALE",
        "🔐 Espaces de travail sécurisés",
        "🌍 Ambition internationale",
        "🤝 Collaboration professionnelle",
        "Bienvenue dans SOW IA",
        "COMMENCEZ VOTRE EXPLORATION",
        "✨ Découvrez ce que SOW IA peut faire avec vous",
    )
    for language in LANGUAGES:
        if language == "Français":
            continue
        for key in keys:
            assert translate(key, language) != key, (language, key)


def test_homepage_uses_the_selected_language_without_changing_account_preference_flow():
    source = Path("app.py").read_text(encoding="utf-8")
    assert 'key="sowia_language"' in source
    assert 'st.session_state["sowia_language"] = saved_language' in source
    assert 'translate_ui("PLATEFORME INTELLIGENTE · VISION INTERNATIONALE", language)' in source
    assert 'translate_ui("Bienvenue dans SOW IA", language)' in source

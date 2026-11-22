from pathlib import Path

from i18n import LANGUAGES, translate


def test_main_hero_and_home_labels_are_translated_for_every_supported_language():
    keys = (
        "PLATEFORME INTELLIGENTE · VISION INTERNATIONALE",
        "🔐 Espaces de travail sécurisés",
        "🌍 Ambition internationale",
        "🤝 Collaboration professionnelle",
        "⌂ Accueil",
        "COMMENCEZ VOTRE EXPLORATION",
    )
    for language in LANGUAGES:
        if language == "Français":
            continue
        for key in keys:
            assert translate(key, language) != key, (language, key)


def test_language_switch_is_bound_to_streamlit_session_state_and_translations_are_used():
    source = Path("app.py").read_text(encoding="utf-8")
    assert 'key="sowia_language"' in source
    assert 'st.session_state["sowia_language"] = saved_language' in source
    assert 'translate_ui("PLATEFORME INTELLIGENTE · VISION INTERNATIONALE", language)' in source
    assert 'translate_ui("Bienvenue dans SOW IA", language)' in source

from pathlib import Path
from i18n import translate

def test_privacy_controls_are_translated_in_all_supported_languages():
    keys = ("🔓 Déverrouiller l’écran", "🔒 Verrouiller maintenant", "Protection d’écran")
    for language in ("English", "Español", "中文", "Deutsch", "العربية"):
        assert all(translate(key, language) != key for key in keys)

def test_home_navigation_cards_have_distinct_artwork_and_preserve_routes():
    source = Path("app.py").read_text(encoding="utf-8")
    assert "def navigation_art_data(destination, index):" in source
    assert "st.image(navigation_art_data(destination, catalog_index), use_container_width=True)" in source
    assert "on_click=go_to_page, args=(destination,)" in source

def test_android_menu_safe_area_and_speech_fallback_are_present():
    source = Path("app.py").read_text(encoding="utf-8")
    assert "safe-area-inset-top" in source
    assert "position: static !important" in source
    assert "voiceschanged" in source

def test_android_launcher_uses_the_new_vitrine():
    root = Path("android/app/src/main/java/com/sowkeys/sowia")
    assert "VitrineActivity::class.java" in (root / "MainActivity.kt").read_text(encoding="utf-8")

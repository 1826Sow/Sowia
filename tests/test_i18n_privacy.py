from pathlib import Path

from i18n import translate


def test_privacy_controls_are_translated_in_all_supported_languages():
    labels = {
        "English": ("🔓 Unlock screen", "🔒 Lock now", "Screen privacy"),
        "Español": ("🔓 Desbloquear pantalla", "🔒 Bloquear ahora", "Privacidad de pantalla"),
        "中文": ("🔓 解锁屏幕", "🔒 立即锁定", "屏幕隐私保护"),
        "Deutsch": ("🔓 Bildschirm entsperren", "🔒 Jetzt sperren", "Bildschirmschutz"),
        "العربية": ("🔓 إلغاء قفل الشاشة", "🔒 قفل الآن", "خصوصية الشاشة"),
    }
    keys = ("🔓 Déverrouiller l’écran", "🔒 Verrouiller maintenant", "Protection d’écran")
    for language, expected in labels.items():
        assert tuple(translate(key, language) for key in keys) == expected


def test_privacy_overlay_covers_the_whole_app_and_keeps_unlock_available():
    source = Path("app.py").read_text(encoding="utf-8")
    assert "body::before {" in source
    assert "backdrop-filter: blur(16px)" in source
    assert ".st-key-sowia_privacy_unlock_main" in source
    assert "env(safe-area-inset-top)" in source

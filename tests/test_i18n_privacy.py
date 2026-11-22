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



def test_navigation_categories_are_translated_for_supported_languages():
    categories = {
        "English": "🌙 App marketplace",
        "Español": "🌙 Mercado de aplicaciones",
        "中文": "🌙 应用市场",
        "Deutsch": "🌙 App-Marktplatz",
        "العربية": "🌙 سوق التطبيقات",
    }
    for language, expected in categories.items():
        assert translate("🌙 Bourse aux applications", language) == expected



def test_main_section_headings_are_translated_in_all_supported_languages():
    expected = {
        "English": "Welcome to SOW IA",
        "Español": "Te damos la bienvenida a SOW IA",
        "中文": "欢迎使用 SOW IA",
        "Deutsch": "Willkommen bei SOW IA",
        "العربية": "مرحباً بك في SOW IA",
    }
    for language, translated in expected.items():
        assert translate("Bienvenue dans SOW IA", language) == translated


def test_static_section_headings_use_the_active_language():
    source = Path("app.py").read_text(encoding="utf-8")
    assert 'st.subheader(translate_ui("Bienvenue dans SOW IA", language))' in source
    assert 'st.subheader(translate_ui("🌙 SOW IA NIGHT EXCHANGE", language))' in source



def test_primary_navigation_controls_are_translated_in_all_supported_languages():
    expected = {
        "English": ("📁 Navigation section", "🧭 Tool to open", "←  BACK TO PREVIOUS PAGE"),
        "Español": ("📁 Sección de navegación", "🧭 Herramienta que abrir", "←  VOLVER A LA PÁGINA ANTERIOR"),
        "中文": ("📁 导航分类", "🧭 要打开的工具", "←  返回上一页"),
        "Deutsch": ("📁 Navigationsbereich", "🧭 Werkzeug öffnen", "←  ZURÜCK ZUR VORHERIGEN SEITE"),
        "العربية": ("📁 قسم التنقل", "🧭 الأداة المراد فتحها", "←  العودة إلى الصفحة السابقة"),
    }
    keys = (
        "📁 Dossier de navigation",
        "🧭 Outil à ouvrir",
        "←  RETOUR À LA PAGE PRÉCÉDENTE",
    )
    for language, translated in expected.items():
        assert tuple(translate(key, language) for key in keys) == translated


def test_primary_navigation_controls_use_the_active_language():
    source = Path("app.py").read_text(encoding="utf-8")
    assert 'translate_ui("📁 Dossier de navigation", language)' in source
    assert 'translate_ui("🧭 Outil à ouvrir", language)' in source
    assert 'translate_ui("←  RETOUR À LA PAGE PRÉCÉDENTE", language)' in source


def test_account_access_labels_are_translated_in_all_supported_languages():
    keys = ("Connexion à mon compte SOW IA", "Créer un compte SOW IA", "Votre adresse e-mail", "Mot de passe (8 caractères minimum)", "Confirmer le mot de passe", "Connexion avec mot de passe", "Connexion par e-mail", "Continuer avec GitHub")
    for language in ("English", "Español", "中文", "Deutsch", "العربية"):
        assert all(translate(key, language) != key for key in keys)


def test_account_access_controls_use_translation_without_changing_validation_button():
    source = Path("app.py").read_text(encoding="utf-8")
    assert 'translate_ui("Connexion à mon compte SOW IA", language)' in source
    assert 'translate_ui("Votre adresse e-mail", language)' in source
    assert 'translate_ui("Mot de passe", language)' in source
    assert 'key="sowia_password_login_submit"' in source
    assert '"VALIDER"' in source


def test_account_validation_messages_are_translated():
    keys = ("Saisissez une adresse e-mail valide.", "Le mot de passe doit contenir au moins 8 caractères.", "Les deux mots de passe ne correspondent pas.", "Saisissez votre mot de passe.", "Connexion impossible. Vérifiez l'adresse e-mail et le mot de passe.")
    for language in ("English", "Español", "中文", "Deutsch", "العربية"):
        assert all(translate(key, language) != key for key in keys)

def test_home_catalog_renders_every_navigation_destination_with_its_own_artwork():
    source = Path("app.py").read_text(encoding="utf-8")
    assert "for section_title, section_pages in NAV_GROUPS.items():" in source
    assert "navigation_art_data(destination, catalog_index)" in source
    assert "data:image/svg+xml;base64," in source
    assert 'key=f"home_group_{destination}"' in source
    assert "with st.expander(section_title, expanded=False)" not in source

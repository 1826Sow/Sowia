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

@pytest.mark.parametrize("language,expected", [
    ("English", "Save"),
    ("Español", "Guardar"),
    ("中文", "保存"),
    ("Deutsch", "Speichern"),
    ("العربية", "حفظ"),
])
def test_common_interface_actions_are_translated(language, expected):
    assert translate("Enregistrer", language) == expected


def test_markdown_headings_keep_formatting_when_translated():
    assert translate("### Vue d'ensemble", "English") == "### Overview"

@pytest.mark.parametrize("language,expected", [
    ("English", "Your secure personal space."),
    ("Español", "Tu espacio personal seguro."),
    ("中文", "您的安全个人空间。"),
    ("Deutsch", "Ihr sicherer persönlicher Bereich."),
    ("العربية", "مساحتك الشخصية الآمنة."),
])
def test_pre_login_workspace_copy_is_localized(language, expected):
    assert translate("Votre espace personnel sécurisé.", language) == expected


@pytest.mark.parametrize("language,expected", [
    ("English", "Sign in with password"),
    ("Español", "Iniciar sesión con contraseña"),
    ("中文", "使用密码登录"),
    ("Deutsch", "Mit Passwort anmelden"),
    ("العربية", "تسجيل الدخول بكلمة المرور"),
])
def test_password_login_heading_is_localized(language, expected):
    assert translate("Connexion avec mot de passe", language) == expected


@pytest.mark.parametrize("language,expected", [
    ("English", "Enter a valid email address."),
    ("Español", "Introduce una dirección de correo electrónico válida."),
    ("中文", "请输入有效的电子邮箱地址。"),
    ("Deutsch", "Geben Sie eine gültige E-Mail-Adresse ein."),
    ("العربية", "أدخل عنوان بريد إلكتروني صالحًا."),
])
def test_signup_validation_feedback_is_localized(language, expected):
    assert translate("Saisissez une adresse e-mail valide.", language) == expected


@pytest.mark.parametrize("language,expected", [
    ("English", "Continue"),
    ("Español", "Continuar"),
    ("中文", "继续"),
    ("Deutsch", "Weiter"),
    ("العربية", "متابعة"),
])
def test_email_signin_action_is_localized(language, expected):
    assert translate("Valider", language) == expected

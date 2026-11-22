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


@pytest.mark.parametrize("source,expected", [
    ("👤 Personnel & documents", "👤 Personal & documents"),
    ("🌐 Écosystème mondial", "🌐 Global ecosystem"),
    ("Hub SOWIA", "SOW IA Hub"),
    ("SOWIA GLOBAL DIRECTORY", "SOW IA GLOBAL DIRECTORY"),
    ("Navigation SOW IA", "SOW IA navigation"),
    ("Toutes les catégories et leurs rubriques sont accessibles ici.", "All categories and their sections are available here."),
])
def test_english_navigation_and_dashboard_are_translated(source, expected):
    assert translate(source, "English") == expected


def test_english_language_selection_does_not_change_internal_french_keys():
    assert translate("Accueil", "English") == "Home"
    assert translate("Accueil", "Français") == "Accueil"


@pytest.mark.parametrize("source,expected", [
    ("💬 Mes échanges & projets", "💬 My conversations & projects"),
    ("＋ Créer un projet", "＋ Create a project"),
    ("Nom du projet", "Project name"),
    ("Description / point de reprise", "Description / handover notes"),
    ("Statut initial", "Initial status"),
    ("Enregistrer le projet", "Save project"),
    ("Vos projets enregistrés", "Your saved projects"),
    ("Livrables associés", "Linked deliverables"),
    ("Modifier le projet", "Edit project"),
    ("Conversation associée", "Linked conversation"),
    ("Consulter les projets archivés", "View archived projects"),
    ("Restaurer", "Restore"),
    ("Aucun projet archivé.", "No archived projects."),
])
def test_english_project_register_labels_are_translated(source, expected):
    assert translate(source, "English") == expected


@pytest.mark.parametrize("source,expected", [
    ("Votre espace personnel sécurisé.", "Your secure personal space."),
    ("Connexion à mon compte SOW IA", "Sign in to my SOW IA account"),
    ("Créer un compte SOW IA", "Create a SOW IA account"),
    ("Votre adresse e-mail", "Your email address"),
    ("Mot de passe (8 caractères minimum)", "Password (at least 8 characters)"),
    ("Confirmer le mot de passe", "Confirm password"),
    ("Créer mon compte", "Create my account"),
    ("Connexion avec mot de passe", "Sign in with password"),
    ("Connexion par e-mail", "Sign in by email"),
    ("Adresse e-mail du compte SOW IA", "Email address for your SOW IA account"),
    ("Continuer avec GitHub", "Continue with GitHub"),
    ("Recommencer la connexion", "Restart sign-in"),
])
def test_english_authentication_labels_are_translated(source, expected):
    assert translate(source, "English") == expected


def test_english_authentication_guidance_and_errors_are_translated():
    assert translate("Saisissez une adresse e-mail valide.", "English") == "Enter a valid email address."
    assert translate("Les deux mots de passe ne correspondent pas.", "English") == "The passwords do not match."
    assert translate(
        "Demande d'inscription envoyée. Ouvrez l'e-mail de confirmation de Supabase pour activer votre compte, puis revenez sur SOW IA pour vous connecter.",
        "English",
    ).startswith("Sign-up request sent.")


@pytest.mark.parametrize("language,expected", [
    ("English", "The passwords do not match."),
    ("Español", "Las contraseñas no coinciden."),
    ("Deutsch", "Die beiden Passwörter stimmen nicht überein."),
    ("中文", "两次输入的密码不一致。"),
    ("العربية", "كلمتا المرور غير متطابقتين."),
])
def test_authentication_password_mismatch_is_translated_in_every_supported_language(language, expected):
    assert translate("Les deux mots de passe ne correspondent pas.", language) == expected


@pytest.mark.parametrize("language,expected", [
    ("English", "Enter a valid email address."),
    ("Español", "Introduce una dirección de correo electrónico válida."),
    ("Deutsch", "Geben Sie eine gültige E-Mail-Adresse ein."),
    ("中文", "请输入有效的电子邮箱地址。"),
    ("العربية", "أدخل عنوان بريد إلكتروني صالحًا."),
])
def test_authentication_email_validation_is_translated_in_every_supported_language(language, expected):
    assert translate("Saisissez une adresse e-mail valide.", language) == expected


@pytest.mark.parametrize("language,expected", [
    ("English", "Create a SOW IA account"),
    ("Español", "Crear una cuenta SOW IA"),
    ("Deutsch", "SOW IA-Konto erstellen"),
    ("中文", "创建 SOW IA 账户"),
    ("العربية", "إنشاء حساب SOW IA"),
])
def test_account_creation_heading_is_translated_in_every_supported_language(language, expected):
    assert translate("Créer un compte SOW IA", language) == expected


@pytest.mark.parametrize("language", ["English", "Español", "Deutsch", "中文", "العربية"])
def test_authentication_guidance_does_not_fall_back_to_french(language):
    sources = [
        "Connectez-vous avec l’adresse e-mail déjà associée à votre compte SOW IA : utilisez votre mot de passe ou demandez un lien sécurisé à usage unique. Aucun compte GitHub n’est nécessaire.",
        "Créez votre compte avec votre adresse e-mail. Vous recevrez un message pour confirmer cette adresse avant de vous connecter.",
        "Après avoir confirmé votre adresse e-mail, vous pourrez vous connecter directement avec votre mot de passe, sans attendre un nouveau lien e-mail.",
        "Saisissez l'adresse e-mail déjà associée à votre compte SOW IA, puis validez. Un lien sécurisé à usage unique sera envoyé ; aucun nouveau compte ne sera créé.",
        "Demande d'inscription envoyée. Ouvrez l'e-mail de confirmation de Supabase pour activer votre compte, puis revenez sur SOW IA pour vous connecter.",
    ]
    for source in sources:
        assert translate(source, language) != source, f"Untranslated authentication text for {language}: {source}"

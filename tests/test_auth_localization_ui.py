from pathlib import Path


def test_signup_panel_is_open_by_default_for_new_visitors():
    source = Path("app.py").read_text(encoding="utf-8")
    assert 'with st.expander(translate_ui("Créer un compte SOW IA — nouveau compte uniquement", language), expanded=True):' in source


def test_signup_feedback_uses_the_pre_authentication_language():
    source = Path("app.py").read_text(encoding="utf-8")
    assert 'st.success(translate_ui("Demande d\'inscription envoyée.' in source
    assert 'st.error(translate_ui("Saisissez une adresse e-mail valide.", language))' in source
    assert 'st.markdown("#### " + translate_ui("Connexion par e-mail", language))' in source


def test_prelogin_instructions_and_errors_are_translated_in_all_supported_languages():
    from i18n import LANGUAGES, translate

    phrases = (
        "Après avoir confirmé votre adresse e-mail, vous pourrez vous connecter directement avec votre mot de passe, sans attendre un nouveau lien e-mail.",
        "Votre adresse e-mail n'est pas encore confirmée. Ouvrez le message de confirmation envoyé par SOW IA, puis réessayez.",
        "Adresse publique HTTPS invalide. Ouvrez SOW IA depuis son adresse Streamlit officielle.",
        "Saisissez l'adresse e-mail déjà associée à votre compte SOW IA, puis validez. Un lien sécurisé à usage unique sera envoyé ; aucun nouveau compte ne sera créé.",
        "Si cette adresse correspond à un compte SOW IA, un lien sécurisé vient d'être envoyé. Consultez aussi les courriers indésirables.",
        "Continuer avec GitHub",
        "La connexion GitHub n'a pas pu être préparée. Vérifiez la configuration de l'adresse HTTPS publique et du fournisseur GitHub dans Supabase.",
    )
    for language in LANGUAGES:
        for phrase in phrases:
            translated = translate(phrase, language, allow_fallback=False)
            if language == "Français":
                assert translated == phrase
            else:
                assert translated != phrase, (language, phrase)


def test_prelogin_static_auth_copy_uses_the_selected_language():
    source = Path("app.py").read_text(encoding="utf-8")
    assert 'translate_ui("Après avoir confirmé votre adresse e-mail' in source
    assert 'translate_ui("Votre adresse e-mail n\'est pas encore confirmée.' in source
    assert 'translate_ui("Saisissez l\'adresse e-mail déjà associée' in source
    assert 'translate_ui("Si cette adresse correspond à un compte SOW IA' in source
    assert 'translate_ui("Continuer avec GitHub", language)' in source

from pathlib import Path


def test_signup_panel_is_open_by_default_for_new_visitors():
    source = Path("app.py").read_text(encoding="utf-8")
    assert 'with st.expander(translate_ui("Créer un compte SOW IA — nouveau compte uniquement", language), expanded=True):' in source


def test_signup_feedback_uses_the_pre_authentication_language():
    source = Path("app.py").read_text(encoding="utf-8")
    assert 'st.success(translate_ui("Demande d\'inscription envoyée.' in source
    assert 'st.error(translate_ui("Saisissez une adresse e-mail valide.", language))' in source
    assert 'st.markdown("#### " + translate_ui("Connexion par e-mail", language))' in source

from pathlib import Path


def test_auth_fallback_errors_do_not_render_raw_exception_details():
    source = Path("app.py").read_text(encoding="utf-8")

    assert 'st.caption(f"Détail technique : {exc}")' not in source
    assert "st.caption(str(exc))" not in source
    assert "Les détails techniques sont masqués pour protéger les informations de connexion." in source
    assert "La connexion sécurisée Supabase n'a pas abouti." in source
    assert "Code technique : {type(exc).__name__}" in source


def test_email_login_change_has_a_separate_existing_account_screen():
    source = Path("app.py").read_text(encoding="utf-8")

    assert 'st.session_state.get("sowia_email_change_view", False)' in source
    assert 'st.session_state["sowia_email_change_view"] = True' in source
    assert 'st.form("sowia_email_change_form"' in source
    assert "Valider cette adresse" in source
    assert "Retour à la connexion" in source
    assert "ne crée aucun nouveau compte" in source
    assert "should_create_user=False" in Path("sowia_supabase_auth.py").read_text(encoding="utf-8")

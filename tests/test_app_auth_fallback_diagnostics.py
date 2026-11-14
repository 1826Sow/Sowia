from pathlib import Path


def test_auth_fallback_errors_do_not_render_raw_exception_details():
    source = Path("app.py").read_text(encoding="utf-8")

    assert 'st.caption(f"Détail technique : {exc}")' not in source
    assert "st.caption(str(exc))" not in source
    assert "Les détails techniques sont masqués pour protéger les informations de connexion." in source
    assert "Connexion à SOW IA" in source
    assert "Envoyer mon lien de connexion" in source


def test_email_login_does_not_create_new_accounts():
    auth_source = Path("sowia_supabase_auth.py").read_text(encoding="utf-8")

    assert "def email_magic_link(" in auth_source
    assert '"should_create_user": False' in auth_source
    assert "def complete_email_login(" in auth_source

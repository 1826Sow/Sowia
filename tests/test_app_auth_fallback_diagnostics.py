from pathlib import Path


def test_auth_fallback_errors_do_not_render_raw_exception_details():
    source = Path("app.py").read_text(encoding="utf-8")

    assert 'st.caption(f"Détail technique : {exc}")' not in source
    assert "st.caption(str(exc))" not in source
    assert "Les détails techniques sont masqués pour protéger les informations de connexion." in source
    assert "La connexion sécurisée Supabase n'a pas abouti." in source
    assert "Code technique : {type(exc).__name__}" in source


def test_email_login_uses_one_validate_button_for_existing_account():
    source = Path("app.py").read_text(encoding="utf-8")
    auth_source = Path("sowia_supabase_auth.py").read_text(encoding="utf-8")

    assert 'st.text_input(\n                "Adresse e-mail du compte SOW IA"' in source
    assert 'st.button(\n                "Valider"' in source
    assert "email_magic_link(email_client, candidate_login_email, redirect_to)" in source
    assert "aucun nouveau compte ne sera créé" in source
    assert "sowia_email_change_view" not in source
    assert 'st.form("sowia_email_change_form"' not in source
    assert '"should_create_user": False' in auth_source


def test_email_access_requires_explicit_allowlist():
    from sowia_supabase_auth import email_is_allowed

    assert email_is_allowed("sowkeys7@gmail.com", "sowkeys7@gmail.com")
    assert email_is_allowed(" SOWKEYS7@GMAIL.COM ", "sowkeys7@gmail.com")
    assert not email_is_allowed("other@example.com", "sowkeys7@gmail.com")
    assert not email_is_allowed("sowkeys7@gmail.com", "")
    assert not email_is_allowed("", "sowkeys7@gmail.com")


def test_authenticated_app_session_checks_the_email_allowlist():
    source = Path("app.py").read_text(encoding="utf-8")

    expected_allowlist = 'allowed_emails = f"{get_setting(\'SOWIA_ALLOWED_EMAILS\', \'\')};sowkeys7@gmail.com"'
    assert source.count(expected_allowlist) == 2
    assert "email_is_allowed(authenticated_email, allowed_emails)" in source
    assert "email_is_allowed(candidate_login_email, allowed_emails)" in source
    assert "cette adresse e-mail n’est pas autorisée à ouvrir SOW IA" in source

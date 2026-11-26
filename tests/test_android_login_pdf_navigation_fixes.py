from pathlib import Path


def test_password_login_uses_mobile_friendly_button_outside_streamlit_form():
    source = Path("app.py").read_text(encoding="utf-8")
    start = source.index('st.markdown("#### " + translate_ui("Connexion avec mot de passe", language))')
    end = source.index('            if password_login_submitted:', start)
    login_block = source[start:end]

    assert 'st.text_input(' in login_block
    assert 'key="sowia_password_login_email"' in login_block
    assert 'key="sowia_password_login_secret"' in login_block
    assert 'st.button(' in login_block
    assert 'key="sowia_password_login_submit"' in login_block
    assert 'st.form(' not in login_block
    assert 'st.form_submit_button(' not in login_block


def test_android_webview_opens_selectable_documents_and_keeps_system_back():
    source = Path(
        "android/app/src/main/java/com/sowkeys/sowia/DashboardActivity.kt"
    ).read_text(encoding="utf-8")

    assert "Intent(Intent.ACTION_OPEN_DOCUMENT)" in source
    assert "Intent.CATEGORY_OPENABLE" in source
    assert 'type = "*/*"' in source
    assert "override fun onShowFileChooser(" in source
    assert "pendingFileChooser?.onReceiveValue(null)" in source
    assert "takePersistableUriPermission" in source
    assert "onBackPressedDispatcher.addCallback" in source
    assert ".st-key-sowia_navigation_back button" in source


def test_navigation_back_control_is_global_before_rubrique_rendering():
    source = Path("app.py").read_text(encoding="utf-8")
    back_control = source.index('key="sowia_navigation_back"')
    first_rubrique = source.index('if page == "Accueil":')

    assert back_control < first_rubrique
    assert "def go_back_navigation():" in source
    assert "sowia_navigation_history" in source

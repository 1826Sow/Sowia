from pathlib import Path


def test_branded_boot_screen_is_rendered_before_heavy_application_imports():
    source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")

    page_config = source.index("st.set_page_config(page_title=\"SOW IA\"")
    boot_screen = source.index("_sowia_boot_placeholder.markdown(")
    settings_import = source.index("from settings import get_setting")

    assert page_config < boot_screen < settings_import
    assert "Votre espace intelligent se prépare…" in source
    assert "Initialisation sécurisée · Chargement des services" in source


def test_boot_screen_is_removed_only_after_authentication_initialization():
    source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")

    clear_boot = source.index("_sowia_boot_placeholder.empty()")
    auth_language_picker = source.index(
        "# The language picker must be available before both registration and sign-in."
    )

    assert clear_boot < auth_language_picker
    assert 'st.session_state["sowia_boot_completed"] = True' in source

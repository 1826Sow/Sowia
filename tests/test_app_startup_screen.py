from pathlib import Path


def test_streamlit_page_configuration_and_viewport_are_present():
    source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")

    page_config = source.index("st.set_page_config(page_title=APP_NAME")
    assert "page_icon=" in source[page_config:page_config + 180]
    assert 'layout="wide"' in source[page_config:page_config + 180]
    assert "html, body { min-height: 100vh !important;" in source
    assert "#root, #root > div, .stApp { min-height: 100vh !important;" in source


def test_mobile_menu_is_positioned_below_android_status_bar():
    source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")

    mobile_rules = source[source.index("@media (max-width: 760px)"):source.index(".hero {")]
    assert "transform: translateY(24px) !important" in mobile_rules
    assert "Keep the menu below Android's status bar and clock." in mobile_rules

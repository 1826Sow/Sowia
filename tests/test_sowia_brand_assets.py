from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_sowia_brand_assets_exist_and_are_valid_svg():
    for relative in (
        "assets/sowia-brain-brand.svg",
        "assets/sowia-brain-icon.svg",
    ):
        asset = ROOT / relative
        assert asset.is_file(), f"Missing SOW IA brand asset: {relative}"
        content = asset.read_text(encoding="utf-8")
        assert content.lstrip().startswith("<svg")
        assert "</svg>" in content


def test_app_uses_the_new_brain_identity_without_removing_navigation():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    assert 'page_icon="assets/sowia-brain-icon.svg"' in app
    assert 'st.image("assets/sowia-brain-brand.svg"' in app
    assert "sowia_navigation_back" in app
    assert "def handle_logout" in app

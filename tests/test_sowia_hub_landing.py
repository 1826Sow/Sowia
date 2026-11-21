from pathlib import Path


def test_hub_landing_uses_midnight_blue_cyan_identity():
    source = Path("app.py").read_text(encoding="utf-8")
    assert ":root { color-scheme: dark; }" in source
    assert "linear-gradient(180deg, #071426" in source
    assert ".sowia-command-center" in source
    assert "Mes échanges &amp; projets" in source


def test_hub_exposes_existing_workspaces_and_honest_project_status_scope():
    source = Path("app.py").read_text(encoding="utf-8")
    assert '"Hub SOWIA", "Accueil", "Assistant IA"' in source
    assert 'active_page = st.session_state.get("page_nav", "Hub SOWIA")' in source
    assert '("↩ Reprendre mes échanges", "Historique"' in source
    assert '("📄 Mes livrables & documents", "Mes documents"' in source
    assert '("🧪 Laboratoire PDF", "Analyse PDF"' in source
    assert '("🌙 SOWIA NIGHT EXCHANGE", "SOWIA NIGHT EXCHANGE"' in source
    assert "Le registre persistant est accessible dans « Mes échanges & projets »" in source
    assert "Les conversations anciennes et les fichiers existants ne sont pas importés automatiquement" in source
    assert "Consulter le protocole Final Tech" in source


def test_mobile_back_control_stays_reachable_after_scrolling():
    source = Path("app.py").read_text(encoding="utf-8")
    assert 'key="sowia_navigation_back_bottom"' in source
    assert 'on_click=go_back_navigation' in source
    assert "bottom: calc(env(safe-area-inset-bottom, 0px) + 14px)" in source
    assert "min-height: 50px" in source
    assert "@media (min-width: 761px)" in source

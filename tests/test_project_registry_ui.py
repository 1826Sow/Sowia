"""Regression checks for the SOW IA project register Hub integration."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_project_register_is_reachable_from_navigation_and_hub():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "import project_registry_ui" in source
    assert '"Hub SOWIA", "Accueil", "Mes échanges & projets", "Assistant IA"' in source
    assert '("💬 Mes échanges & projets", "Mes échanges & projets"' in source
    assert 'elif page == "Mes échanges & projets":' in source
    assert "project_registry_ui.render(" in source


def test_project_register_ui_enforces_premium_and_reports_import_limits():
    source = (ROOT / "project_registry_ui.py").read_text(encoding="utf-8")
    assert 'workspace_id == "professional" and not premium_active' in source
    assert "Aucun projet ne sera enregistré dans un espace local non synchronisé" in source
    assert "Les conversations anciennes et les fichiers déjà présents ne sont pas importés automatiquement" in source
    assert 'st.session_state.page_nav = "Assistant IA"' in source

"""Regression checks for the SOW IA project register Hub integration."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_project_register_is_reachable_from_navigation_and_hub():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "import project_registry_ui" in source
    assert '"Hub SOWIA", "Accueil", "Assistant IA", "Ma mémoire"' in source
    assert '"📚 Échanges & projets": [' in source
    assert '"Mes échanges & projets", "Historique"' in source
    assert '("💬 Mes échanges & projets", "Mes échanges & projets"' in source
    assert 'elif page == "Mes échanges & projets":' in source
    assert "project_registry_ui.render(" in source


def test_project_register_ui_enforces_premium_and_reports_import_limits():
    source = (ROOT / "project_registry_ui.py").read_text(encoding="utf-8")
    app_source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert 'workspace_id == "professional" and not premium_active' in source
    migration = (ROOT / "supabase/migrations/20261114000100_sowia_project_register.sql").read_text(encoding="utf-8")
    assert migration.count("public.sowia_has_professional_access()") == 4
    assert "workspace_id = 'personal' or public.sowia_has_professional_access()" in migration
    assert "Aucun projet ne sera enregistré dans un espace local non synchronisé" in source
    assert "Les conversations anciennes et les fichiers déjà présents ne sont pas importés automatiquement" in source
    assert 'st.session_state["sowia_resume_session_id"] = session_id' in source
    assert 'resume_session_id = st.session_state.pop("sowia_resume_session_id", None)' in app_source



def test_project_deliverable_links_require_valid_https_without_credentials():
    source = (ROOT / "project_registry_ui.py").read_text(encoding="utf-8")
    assert "def _safe_https_url(value):" in source
    assert "parsed.scheme.lower() != \"https\"" in source
    assert "parsed.username is not None or parsed.password is not None" in source
    assert "_safe_https_url(url)" in source
    assert "_safe_https_url(deliverable_url)" in source
    assert "Lien masqué : seule une adresse HTTPS valide est acceptée." in source

def test_new_projects_can_auto_link_the_active_conversation():
    source = (ROOT / "project_registry_ui.py").read_text(encoding="utf-8")
    assert 'active_session_id = str(st.session_state.get("session_id") or "").strip()' in source
    assert 'Associer automatiquement la conversation en cours' in source
    assert 'value=bool(active_session_id)' in source
    assert 'conversation_session_id=active_session_id if attach_current_session else None' in source
    assert "Aucune conversation active à associer pour le moment." in source

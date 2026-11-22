"""Regression checks for safe project-linked memory."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_project_linked_memory_migration_is_additive_and_workspace_scoped():
    migration = (ROOT / "supabase/migrations/20261122140000_sowia_project_linked_memory.sql").read_text(encoding="utf-8")
    assert "add column if not exists project_id bigint" in migration
    assert "on delete set null" in migration
    assert "p.user_id = sowia_memory_items.user_id" in migration
    assert "p.workspace_id = sowia_memory_items.workspace_id" in migration
    assert "project_id is null" in migration


def test_assistant_retrieves_general_and_selected_project_memory_only():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "Contexte de projet pour cette conversation" in source
    assert "active_memory_project_id is not None" in source
    assert 'item.get("project_id") is None' in source
    assert 'project_id=st.session_state.get("sowia_active_memory_project_id")' in source


def test_memory_page_can_associate_notes_with_registered_projects():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "Associer cette note à un projet" in source
    assert "add_app_memory(note, project_id=selected_memory_project_id)" in source
    assert "Note liée à un projet de cet espace" in source

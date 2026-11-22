from pathlib import Path


def test_memory_search_migration_uses_invoker_and_owner_scope():
    sql = Path("supabase/migrations/20261122120000_sowia_memory_intelligence.sql").read_text(encoding="utf-8")
    assert "SECURITY INVOKER" in sql
    assert "m.user_id = (SELECT auth.uid())" in sql
    assert "m.workspace_id = p_workspace_id" in sql
    assert "m.session_id IS DISTINCT FROM p_exclude_session_id" in sql
    assert "REVOKE ALL ON FUNCTION" in sql
    assert "GRANT EXECUTE ON FUNCTION" in sql


def test_memory_schema_has_no_arbitrary_note_count_and_supports_long_notes():
    sql = Path("supabase/migrations/20261122120000_sowia_memory_intelligence.sql").read_text(encoding="utf-8")
    assert "char_length(content) BETWEEN 1 AND 20000" in sql
    assert "importance BETWEEN 1 AND 5" in sql
    assert "sowia_memory_items_search_idx" in sql
    assert "sowia_messages_search_idx" in sql


def test_project_memory_links_are_owner_and_workspace_scoped():
    sql = Path("supabase/migrations/20261122123000_sowia_memory_project_scope_guard.sql").read_text(encoding="utf-8")
    assert "SECURITY INVOKER" in sql
    assert "p.user_id = NEW.user_id" in sql
    assert "p.workspace_id = NEW.workspace_id" in sql
    assert "p.archived_at IS NULL" in sql

"""Regression guards for the Personal/Professional Supabase schema migration."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = (ROOT / "supabase_schema.sql").read_text(encoding="utf-8").lower()


def test_existing_memory_and_message_rows_are_migrated_to_personal_safely():
    for table in ("sowia_memory_items", "sowia_messages"):
        assert re.search(
            rf"alter table public\\.{table}\\s+add column if not exists workspace_id text not null default 'personal'",
            SCHEMA,
        )
    assert "drop table" not in SCHEMA
    assert "delete from public.sowia_memory_items" not in SCHEMA
    assert "delete from public.sowia_messages" not in SCHEMA


def test_workspace_values_are_limited_to_personal_and_professional():
    for table in ("sowia_memory_items", "sowia_messages"):
        assert re.search(
            rf"alter table public\\.{table}.*?add constraint {table}_workspace_id_check\\s+check \\(workspace_id in \\('personal', 'professional'\\)\\)",
            SCHEMA,
            flags=re.DOTALL,
        )


def test_workspace_queries_have_composite_indexes():
    assert re.search(
        r"on public\\.sowia_memory_items \\(user_id, workspace_id, created_at desc\\)",
        SCHEMA,
    )
    assert re.search(
        r"on public\\.sowia_messages \\(user_id, workspace_id, session_id, id desc\\)",
        SCHEMA,
    )


def test_workspace_migration_keeps_row_level_security_enabled():
    for table in ("sowia_memory_items", "sowia_messages"):
        assert re.search(
            rf"alter table public\\.{table} enable row level security",
            SCHEMA,
        )

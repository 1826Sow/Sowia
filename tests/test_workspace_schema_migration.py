"""Regression guards for the Personal/Professional Supabase schema migration."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = (ROOT / "supabase_schema.sql").read_text(encoding="utf-8").lower()


def test_existing_rows_are_migrated_to_personal_without_deletion():
    for table in ("sowia_memory_items", "sowia_messages"):
        statement = (
            f"alter table public.{table} "
            "add column if not exists workspace_id text not null default 'personal'"
        )
        assert statement in " ".join(SCHEMA.split())
    assert "drop table" not in SCHEMA
    assert "delete from public.sowia_memory_items" not in SCHEMA
    assert "delete from public.sowia_messages" not in SCHEMA


def test_workspace_values_are_limited_to_supported_workspaces():
    for table in ("sowia_memory_items", "sowia_messages"):
        assert f"add constraint {table}_workspace_id_check" in SCHEMA
    # Each table has a CREATE TABLE constraint and an idempotent migration guard.
    assert SCHEMA.count("check (workspace_id in ('personal', 'professional'))") == 4


def test_workspace_queries_have_composite_indexes():
    normalized = " ".join(SCHEMA.split())
    assert (
        "on public.sowia_memory_items "
        "(user_id, workspace_id, created_at desc)" in normalized
    )
    assert (
        "on public.sowia_messages "
        "(user_id, workspace_id, session_id, id desc)" in normalized
    )


def test_workspace_migration_keeps_row_level_security_enabled():
    for table in ("sowia_memory_items", "sowia_messages"):
        assert f"alter table public.{table} enable row level security" in SCHEMA

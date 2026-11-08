"""Regression checks for the private Supabase Storage SQL policies.

These checks validate the repository's intended SQL shape only. They do not
replace executing the scripts and testing two authenticated users in Supabase.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICIES = (ROOT / "supabase_storage_policies.sql").read_text(encoding="utf-8").lower()
DIAGNOSTICS = (ROOT / "supabase_storage_diagnostics.sql").read_text(encoding="utf-8").lower()


def test_private_bucket_is_not_public_and_restricts_pdf_uploads():
    assert "'sowia-files', 'sowia-files', false" in POLICIES
    assert "file_size_limit = 10485760" in POLICIES
    assert "array['application/pdf']" in POLICIES


def test_storage_read_and_delete_policies_require_authenticated_owner():
    for command in ("select", "delete"):
        assert f"on storage.objects for {command} to authenticated" in POLICIES
    assert POLICIES.count("(storage.foldername(name))[1] = (select auth.uid())::text") == 3


def test_storage_upload_policy_requires_owner_and_valid_workspace_folder():
    assert "on storage.objects for insert to authenticated" in POLICIES
    assert "with check (" in POLICIES
    assert "array_length(storage.foldername(name), 1) = 2" in POLICIES
    assert "(storage.foldername(name))[2] in ('personal', 'professional')" in POLICIES


def test_storage_policy_removes_legacy_broader_policy_names():
    assert 'drop policy if exists "sow ia users read own documents"' in POLICIES
    assert 'drop policy if exists "sow ia users upload own documents"' in POLICIES
    assert 'drop policy if exists "sow ia users delete own documents"' in POLICIES


def test_storage_diagnostic_is_read_only_and_reports_all_object_policies():
    assert "from pg_policies" in DIAGNOSTICS
    assert "where schemaname = 'storage'" in DIAGNOSTICS
    assert "and tablename = 'objects'" in DIAGNOSTICS
    assert not any(
        statement in DIAGNOSTICS
        for statement in ("create policy", "drop policy", "alter table", "delete from", "update ")
    )

SCHEMA = (ROOT / "supabase" / "schema.sql").read_text(encoding="utf-8").lower()
WORKSPACES = (ROOT / "supabase_workspaces.sql").read_text(encoding="utf-8").lower()


def test_authenticated_sequence_grants_are_limited_to_required_identity_sequences():
    assert "grant usage, select on sequence" in SCHEMA
    assert "public.sowia_messages_id_seq" in SCHEMA
    assert "public.sowia_memory_items_id_seq" in SCHEMA
    assert "on all sequences in schema public" not in SCHEMA


def test_workspace_migration_adds_and_constrains_workspace_columns():
    for table in ("sowia_messages", "sowia_memory_items"):
        assert f"alter table public.{table} add column if not exists workspace_id text not null default 'personal'" in WORKSPACES
        assert f"alter table public.{table} add constraint {table}_workspace_id_check" in WORKSPACES
    assert "check (workspace_id in ('personal', 'professional'))" in WORKSPACES

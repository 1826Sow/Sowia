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


def test_cloud_tables_enable_rls_and_scope_policies_to_authenticated_owner():
    for table in ("sowia_messages", "sowia_memory_items", "sowia_entitlements"):
        assert f"alter table public.{table} enable row level security" in SCHEMA
    for policy in (
        "users can read own messages",
        "users can add own messages",
        "users can delete own messages",
        "users can read own memory",
        "users can add own memory",
        "users can delete own memory",
        "users can read own premium entitlement",
    ):
        assert f'create policy "{policy}"' in SCHEMA
    assert SCHEMA.count("(select auth.uid()) = user_id") == 7


def test_authenticated_users_cannot_write_their_own_premium_entitlement():
    entitlement_grants = [
        line.strip()
        for line in SCHEMA.splitlines()
        if line.strip().startswith("grant ") and "sowia_entitlements" in line
    ]
    assert entitlement_grants == [
        "grant select on public.sowia_entitlements to authenticated;"
    ]


SEQUENCE_DIAGNOSTICS = (
    ROOT / "supabase_sequence_grants_diagnostics.sql"
).read_text(encoding="utf-8").lower()


def test_sequence_privilege_diagnostic_is_read_only_and_checks_effective_access():
    assert "has_sequence_privilege('authenticated'" in SEQUENCE_DIAGNOSTICS
    assert "sowia_messages_id_seq" in SEQUENCE_DIAGNOSTICS
    assert "sowia_memory_items_id_seq" in SEQUENCE_DIAGNOSTICS
    assert "from pg_class" in SEQUENCE_DIAGNOSTICS
    assert not any(
        statement in SEQUENCE_DIAGNOSTICS
        for statement in ("grant ", "revoke ", "alter ", "drop ", "delete from", "update ")
    )


RLS_STORAGE_DIAGNOSTICS = (
    ROOT / "supabase_rls_storage_diagnostics.sql"
).read_text(encoding="utf-8").lower()


def test_rls_and_storage_diagnostic_is_read_only_and_covers_security_metadata():
    assert "from pg_class" in RLS_STORAGE_DIAGNOSTICS
    assert "relrowsecurity" in RLS_STORAGE_DIAGNOSTICS
    assert "from pg_policies" in RLS_STORAGE_DIAGNOSTICS
    assert "sowia_messages" in RLS_STORAGE_DIAGNOSTICS
    assert "sowia_memory_items" in RLS_STORAGE_DIAGNOSTICS
    assert "sowia_entitlements" in RLS_STORAGE_DIAGNOSTICS
    assert "from storage.buckets" in RLS_STORAGE_DIAGNOSTICS
    assert "where id = 'sowia-files'" in RLS_STORAGE_DIAGNOSTICS
    assert "where schemaname = 'storage'" in RLS_STORAGE_DIAGNOSTICS
    assert "and tablename = 'objects'" in RLS_STORAGE_DIAGNOSTICS
    assert not any(
        statement in RLS_STORAGE_DIAGNOSTICS
        for statement in (
            "create policy", "drop policy", "alter table", "grant ",
            "revoke ", "insert into", "delete from", "update "
        )
    )


def test_legacy_root_paths_are_readable_and_deletable_but_not_uploadable():
    # One folder component means <user_id>/<legacy-file.pdf>.
    # Keep this compatibility for existing Personal files only.
    assert "array_length(storage.foldername(name), 1) = 1" in POLICIES
    assert "on storage.objects for select to authenticated" in POLICIES
    assert "on storage.objects for delete to authenticated" in POLICIES

    # New uploads must always include a workspace folder.
    insert_policy = POLICIES.split(
        'on storage.objects for insert to authenticated', 1
    )[1].split(";", 1)[0]
    assert "array_length(storage.foldername(name), 1) = 2" in insert_policy
    assert "(storage.foldername(name))[2] in ('personal', 'professional')" in insert_policy

"""Static safeguards for the optional Supabase storage and Premium SQL setup.
These tests do not connect to Supabase or execute SQL.
"""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SQL_PATH = ROOT / "supabase_optional_features.sql"
SCHEMA_PATH = ROOT / "supabase" / "schema.sql"


def _sql():
    return SQL_PATH.read_text(encoding="utf-8").lower()


def test_private_pdf_bucket_is_not_public_and_has_upload_limits():
    sql = _sql()
    assert "'sowia-private-documents'" in sql
    assert "false" in sql
    assert "10485760" in sql
    assert "application/pdf" in sql


def test_pdf_storage_policies_scope_every_operation_to_authenticated_owner():
    sql = _sql()
    policy_sections = [
        sql.split('create policy "sow ia users read own private pdfs"', 1)[1].split(";", 1)[0],
        sql.split('create policy "sow ia users upload own private pdfs"', 1)[1].split(";", 1)[0],
        sql.split('create policy "sow ia users update own private pdfs"', 1)[1].split(";", 1)[0],
        sql.split('create policy "sow ia users delete own private pdfs"', 1)[1].split(";", 1)[0],
    ]
    for section in policy_sections:
        assert "to authenticated" in section
        assert "bucket_id = 'sowia-private-documents'" in section
        assert "auth.uid()" in section


def test_premium_entitlements_are_user_scoped_and_not_client_writable():
    sql = _sql()
    assert "create table if not exists public.sowia_entitlements" in sql
    assert "enable row level security" in sql
    assert "using ((select auth.uid()) = user_id)" in sql
    assert "revoke all on public.sowia_entitlements from public, anon, authenticated" in sql
    assert "grant select on public.sowia_entitlements to authenticated" in sql
    assert "grant insert" not in sql
    assert "grant update" not in sql
    assert "grant delete" not in sql


def test_existing_pdf_bucket_is_never_reconfigured_automatically():
    sql = _sql()
    bucket_setup = sql.split("insert into storage.buckets", 1)[1].split("-- a user's files", 1)[0]
    assert "on conflict (id) do nothing" in bucket_setup
    assert "do update" not in bucket_setup


def test_memory_and_history_schema_uses_owner_scoped_rls():
    sql = SCHEMA_PATH.read_text(encoding="utf-8").lower()
    for table in ("sowia_messages", "sowia_memory_items"):
        assert f"alter table public.{table} enable row level security" in sql
    assert "for select to authenticated" in sql
    assert "for insert to authenticated" in sql
    assert "for delete to authenticated" in sql
    assert "using ((select auth.uid()) = user_id)" in sql
    assert "with check ((select auth.uid()) = user_id)" in sql


def test_memory_and_history_table_privileges_are_explicitly_restricted():
    sql = SCHEMA_PATH.read_text(encoding="utf-8").lower()
    assert (
        "revoke all on table public.sowia_messages, public.sowia_memory_items "
        "from public, anon, authenticated"
    ) in " ".join(sql.split())
    assert "grant select, insert, delete on public.sowia_messages to authenticated" in sql
    assert "grant select, insert, delete on public.sowia_memory_items to authenticated" in sql
    assert "grant update on public.sowia_messages" not in sql
    assert "grant update on public.sowia_memory_items" not in sql


def test_memory_and_history_sequence_grants_are_narrowly_scoped():
    sql = SCHEMA_PATH.read_text(encoding="utf-8").lower()
    assert "on all sequences in schema public" not in sql
    assert "public.sowia_messages_id_seq" in sql
    assert "public.sowia_memory_items_id_seq" in sql
    assert "revoke all on sequence" in sql


def test_memory_schema_allows_the_documented_premium_note_limit():
    sql = SCHEMA_PATH.read_text(encoding="utf-8").lower()
    assert "content text not null check (char_length(content) between 1 and 5000)" in sql


def test_entitlement_statuses_match_in_both_sql_setup_paths():
    canonical = SCHEMA_PATH.read_text(encoding="utf-8").lower()
    optional = _sql()
    expected = "status text not null check (status in ('active', 'inactive', 'cancelled'))"
    assert expected in canonical
    assert expected in optional


def test_canonical_schema_also_revokes_client_write_privileges_on_entitlements():
    canonical = SCHEMA_PATH.read_text(encoding="utf-8").lower()
    assert "revoke all on public.sowia_entitlements from public, anon, authenticated" in canonical
    assert "grant select on public.sowia_entitlements to authenticated" in canonical



def test_private_storage_guard_is_restrictive_against_legacy_policies():
    sql = _sql()
    marker = 'create policy "sow ia enforce private pdf folder isolation"'
    assert marker in sql
    section = sql.split(marker, 1)[1].split(";", 1)[0]
    assert "as restrictive" in section
    assert "for all" in section
    assert "to public" in section
    assert "bucket_id <> 'sowia-private-documents'" in section
    assert "(storage.foldername(name))[1]" in section
    assert "auth.uid()" in section
    assert "using (" in section
    assert "with check (" in section


def test_existing_bucket_configuration_is_not_overwritten():
    sql = _sql()
    bucket_setup = sql.split("insert into storage.buckets", 1)[1].split(";", 1)[0]
    assert "on conflict (id) do nothing" in bucket_setup
    assert "do update" not in bucket_setup
    assert "set public" not in bucket_setup


def test_optional_and_canonical_schema_use_the_same_entitlement_read_policy():
    optional = _sql()
    canonical = SCHEMA_PATH.read_text(encoding="utf-8").lower()
    policy = '"users can read own premium entitlement"'
    assert f"drop policy if exists {policy}" in optional
    assert f"create policy {policy}" in optional
    assert f"drop policy if exists {policy}" in canonical
    assert f"create policy {policy}" in canonical

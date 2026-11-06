"""Static safeguards for the optional Supabase storage and Premium SQL setup.

These tests do not connect to Supabase or execute SQL. They protect the
intended least-privilege configuration from accidental edits.
"""
from pathlib import Path


SQL_PATH = Path(__file__).resolve().parents[1] / "supabase_optional_features.sql"


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


def test_restrictive_storage_guard_blocks_other_users_even_with_permissive_policies():
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

def test_existing_bucket_configuration_is_never_overwritten_automatically():
    sql = _sql()
    bucket_setup = sql.split("insert into storage.buckets", 1)[1].split(";", 1)[0]
    assert "on conflict (id) do nothing" in bucket_setup
    assert "do update" not in bucket_setup
    assert "set public" not in bucket_setup
    assert "set file_size_limit" not in bucket_setup
    assert "set allowed_mime_types" not in bucket_setup


def test_entitlement_table_revokes_default_public_and_client_privileges():
    sql = _sql()
    assert "revoke all on public.sowia_entitlements from public, anon, authenticated" in sql
    assert "grant select on public.sowia_entitlements to authenticated" in sql

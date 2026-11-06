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
    assert "revoke all on public.sowia_entitlements from anon, authenticated" in sql
    assert "grant select on public.sowia_entitlements to authenticated" in sql
    assert "grant insert" not in sql
    assert "grant update" not in sql
    assert "grant delete" not in sql

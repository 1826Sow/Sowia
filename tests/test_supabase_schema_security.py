"""Regression checks for the Supabase SQL security contract.

These tests inspect the migration source; they do not replace applying it to
an isolated Supabase project and testing with real authenticated accounts.
"""
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = (ROOT / "supabase" / "schema.sql").read_text(encoding="utf-8")
STORAGE = (ROOT / "supabase" / "storage.sql").read_text(encoding="utf-8")


def _policy_block(sql, policy_name):
    match = re.search(
        rf'create policy "{re.escape(policy_name)}".*?;',
        sql,
        flags=re.IGNORECASE | re.DOTALL,
    )
    assert match, f"Missing policy: {policy_name}"
    return match.group(0).lower()


def test_user_tables_enable_rls_and_scope_every_operation_to_auth_uid():
    for table in ("sowia_messages", "sowia_memory_items"):
        assert f"alter table public.{table} enable row level security" in SCHEMA.lower()
        assert f'create policy "users can read own' in SCHEMA.lower()
        assert f'create policy "users can add own' in SCHEMA.lower()
        assert f'create policy "users can delete own' in SCHEMA.lower()

    for name in (
        "Users can read own messages",
        "Users can add own messages",
        "Users can delete own messages",
        "Users can read own memory",
        "Users can add own memory",
        "Users can delete own memory",
    ):
        block = _policy_block(SCHEMA, name)
        assert "auth.uid()" in block
        assert "user_id" in block
        assert "to authenticated" in block


def test_client_grants_are_least_privilege_and_entitlements_are_read_only():
    sql = SCHEMA.lower()
    assert "revoke all on table\n    public.sowia_messages,\n    public.sowia_memory_items\nfrom anon, authenticated" in sql
    assert "grant select, insert, delete on public.sowia_messages to authenticated" in sql
    assert "grant select, insert, delete on public.sowia_memory_items to authenticated" in sql
    assert "revoke all on table public.sowia_entitlements from anon, authenticated" in sql
    assert "grant select on public.sowia_entitlements to authenticated" in sql
    assert "grant insert" not in re.sub(
        r"grant select, insert, delete on public\.sowia_(?:messages|memory_items) to authenticated",
        "",
        sql,
    )


def test_private_pdf_bucket_is_limited_and_has_owner_scoped_policies():
    for sql in (SCHEMA.lower(), STORAGE.lower()):
        assert "'sowia-private-documents'" in sql
        assert "false" in sql
        assert "10485760" in sql
        assert "application/pdf" in sql
        assert "storage.foldername(name)" in sql
        assert "auth.uid()" in sql
        assert "to authenticated" in sql
        assert "for select" in sql
        assert "for insert" in sql
        assert "for delete" in sql

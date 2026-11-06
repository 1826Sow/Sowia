"""Regression checks for the Supabase SQL security contract.

These tests inspect migration source; they do not replace applying it to an
isolated Supabase project and testing with real authenticated accounts.
"""
from pathlib import Path
import re

import document_storage


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


def test_each_user_table_has_owner_scoped_read_insert_and_delete_policies():
    sql = SCHEMA.lower()
    table_policies = {
        "sowia_messages": (
            "Users can read own messages",
            "Users can add own messages",
            "Users can delete own messages",
        ),
        "sowia_memory_items": (
            "Users can read own memory",
            "Users can add own memory",
            "Users can delete own memory",
        ),
    }

    for table, policy_names in table_policies.items():
        assert f"alter table public.{table} enable row level security" in sql
        for name in policy_names:
            block = _policy_block(SCHEMA, name)
            assert f"on public.{table}" in block
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


def test_private_pdf_bucket_is_limited_and_has_owner_scoped_policies():
    for sql in (SCHEMA.lower(), STORAGE.lower()):
        assert "'sowia-private-documents'" in sql
        assert "public = false" in sql
        assert "10485760" in sql
        assert "application/pdf" in sql
        assert "storage.foldername(name)" in sql
        assert "(select auth.uid())::text" in sql
        assert "to authenticated" in sql
        assert "for select" in sql
        assert "for insert" in sql
        assert "for delete" in sql


def test_document_storage_uses_the_same_uuid_folder_as_supabase_rls():
    class AuthenticatedUser:
        id = "11111111-1111-1111-1111-111111111111"

    prefix = document_storage._user_prefix(AuthenticatedUser())
    assert prefix == AuthenticatedUser.id
    assert f"(storage.foldername(name))[1] = (select auth.uid())::text" in SCHEMA

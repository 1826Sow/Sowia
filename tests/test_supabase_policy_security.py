"""Regression guards for the canonical Supabase schema and private PDF storage."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = (ROOT / "supabase" / "schema.sql").read_text(encoding="utf-8").lower()
STORAGE = (ROOT / "supabase_storage_policies.sql").read_text(encoding="utf-8").lower()
GLOBAL_ID = (ROOT / "supabase_global_id.sql").read_text(encoding="utf-8").lower()


def _policy_block(sql, policy_name):
    match = re.search(
        rf'create policy "{re.escape(policy_name.lower())}"(.*?);',
        sql,
        flags=re.DOTALL,
    )
    assert match, f"Missing policy: {policy_name}"
    return match.group(1)


def test_canonical_private_tables_keep_row_level_security_enabled():
    for table in ("sowia_memory_items", "sowia_messages", "sowia_entitlements"):
        assert re.search(
            rf"alter table public\.{table} enable row level security",
            SCHEMA,
        )


def test_memory_and_message_policies_are_limited_to_authenticated_owner():
    for table, label in (
        ("sowia_memory_items", "memory"),
        ("sowia_messages", "messages"),
    ):
        read = _policy_block(SCHEMA, f"Users can read own {label}")
        insert = _policy_block(SCHEMA, f"Users can add own {label}")
        delete = _policy_block(SCHEMA, f"Users can delete own {label}")
        for block in (read, insert, delete):
            assert "to authenticated" in block
            assert "auth.uid()" in block
            assert "user_id" in block
        assert "with check" in insert
        assert "using" in read
        assert "using" in delete


def test_premium_entitlement_is_read_only_for_authenticated_users():
    block = _policy_block(SCHEMA, "Users can read own Premium entitlement")
    assert "for select to authenticated" in block
    assert "auth.uid()" in block
    assert "user_id" in block
    assert re.search(
        r"grant select on public\.sowia_entitlements to authenticated",
        SCHEMA,
    )
    assert not re.search(
        r"grant (?:insert|update|delete|all).*sowia_entitlements to authenticated",
        SCHEMA,
    )


def test_pdf_bucket_is_private_and_restricted_to_pdf_files():
    assert "'sowia-files', 'sowia-files', false, 10485760" in STORAGE
    assert "array['application/pdf']" in STORAGE


def test_pdf_read_and_delete_policies_require_authenticated_owner():
    for label in ("read", "delete"):
        block = _policy_block(
            STORAGE,
            f"SOW IA users can {label} own workspace PDFs",
        )
        assert "to authenticated" in block
        assert "bucket_id = 'sowia-files'" in block
        assert "auth.uid()" in block
        assert "personal" in block
        assert "professional" in block


def test_pdf_upload_policy_requires_owner_and_exact_workspace_folder():
    block = _policy_block(STORAGE, "SOW IA users can upload own workspace PDFs")
    assert "to authenticated" in block
    assert "bucket_id = 'sowia-files'" in block
    assert "auth.uid()" in block
    assert "array_length(storage.foldername(name), 1) = 2" in block
    assert "personal" in block
    assert "professional" in block


def test_global_id_trigger_prevents_self_verification():
    assert "before insert or update on public.sowia_global_profiles" in GLOBAL_ID
    assert "if not is_admin then" in GLOBAL_ID
    assert "new.verification_status := old.verification_status" in GLOBAL_ID
    assert "new.verification_evidence_reference := old.verification_evidence_reference" in GLOBAL_ID
    assert "new.verified_at := old.verified_at" in GLOBAL_ID

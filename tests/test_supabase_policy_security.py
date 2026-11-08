"""Regression guards for Supabase row-level and PDF object policies."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = (ROOT / "supabase_schema.sql").read_text(encoding="utf-8").lower()
STORAGE = (ROOT / "supabase_storage_policies.sql").read_text(encoding="utf-8").lower()


def _policy_block(sql, policy_name):
    match = re.search(
        rf'create policy "{re.escape(policy_name.lower())}"(.*?);',
        sql,
        flags=re.DOTALL,
    )
    assert match, f"Missing policy: {policy_name}"
    return match.group(1)


def test_private_tables_keep_row_level_security_enabled():
    assert re.search(
        r"alter table public\.sowia_memory_items enable row level security",
        SCHEMA,
    )
    assert re.search(
        r"alter table public\.sowia_messages enable row level security",
        SCHEMA,
    )


def test_memory_and_message_policies_are_limited_to_authenticated_owner():
    for table, label in (
        ("sowia_memory_items", "memories"),
        ("sowia_messages", "messages"),
    ):
        read = _policy_block(SCHEMA, f"Users can read their own SOW IA {label}")
        insert = _policy_block(SCHEMA, f"Users can add their own SOW IA {label}")
        delete = _policy_block(SCHEMA, f"Users can delete their own SOW IA {label}")
        for block in (read, insert, delete):
            assert "to authenticated" in block
            assert "auth.uid()" in block
            assert "user_id" in block
        assert "with check" in insert
        assert "using" in read
        assert "using" in delete


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


LEGACY_STORAGE = (
    ROOT / "supabase" / "storage.sql"
).read_text(encoding="utf-8").lower()


def test_legacy_storage_script_keeps_the_same_private_bucket_settings():
    for sql in (STORAGE, LEGACY_STORAGE):
        assert "'sowia-files', 'sowia-files', false, 10485760" in sql
        assert "array['application/pdf']" in sql


def test_legacy_storage_script_removes_old_permissive_policy_names():
    old_names = (
        "sow ia users read own documents",
        "sow ia users upload own documents",
        "sow ia users delete own documents",
    )
    for sql in (STORAGE, LEGACY_STORAGE):
        for name in old_names:
            assert f'drop policy if exists "{name}"' in sql


def test_legacy_and_canonical_storage_scripts_use_matching_workspace_rules():
    policy_names = (
        "SOW IA users can read own workspace PDFs",
        "SOW IA users can upload own workspace PDFs",
        "SOW IA users can delete own workspace PDFs",
    )
    for name in policy_names:
        assert _policy_block(STORAGE, name) == _policy_block(LEGACY_STORAGE, name)



def test_all_storage_policies_restrict_access_to_pdf_objects():
    policy_names = (
        "SOW IA users can read own workspace PDFs",
        "SOW IA users can upload own workspace PDFs",
        "SOW IA users can delete own workspace PDFs",
    )
    for sql in (STORAGE, LEGACY_STORAGE):
        for name in policy_names:
            assert "lower(name) like '%.pdf'" in _policy_block(sql, name)

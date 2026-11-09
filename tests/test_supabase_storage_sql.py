from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = (ROOT / "supabase" / "schema.sql").read_text(encoding="utf-8")
STORAGE = (ROOT / "supabase" / "storage_security.sql").read_text(encoding="utf-8")


def test_cloud_tables_define_workspace_scope_and_migrate_existing_rows():
    assert SCHEMA.count("workspace_id text") >= 2
    assert "update public.sowia_messages set workspace_id = 'personal' where workspace_id is null" in SCHEMA
    assert "update public.sowia_memory_items set workspace_id = 'personal' where workspace_id is null" in SCHEMA
    assert "sowia_messages_user_workspace_session_idx" in SCHEMA
    assert "sowia_memory_user_workspace_created_idx" in SCHEMA
    assert SCHEMA.count("check (workspace_id in ('personal', 'professional'))") >= 2


def test_pdf_bucket_is_private_and_limited_to_ten_megabytes_and_pdf():
    assert "'sowia-files'" in STORAGE
    assert "public = false" in STORAGE
    assert "10485760" in STORAGE
    assert "array['application/pdf']::text[]" in STORAGE


def test_storage_policies_scope_objects_to_authenticated_user_folder():
    assert STORAGE.count("bucket_id = 'sowia-files'") == 3
    assert STORAGE.count("(storage.foldername(name))[1] = (select auth.uid()::text)") == 3
    assert 'for select' in STORAGE
    assert 'for insert' in STORAGE
    assert 'for delete' in STORAGE


def test_storage_setup_is_repeatable():
    assert STORAGE.count("drop policy if exists") == 3
    assert "on conflict (id) do update" in STORAGE

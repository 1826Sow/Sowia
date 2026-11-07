"""Regression checks for the Supabase schema security contract."""
from pathlib import Path

import document_storage


SCHEMA = Path(__file__).resolve().parents[1] / "supabase_schema.sql"


def test_private_document_bucket_matches_application_configuration():
    sql = SCHEMA.read_text(encoding="utf-8")
    bucket = document_storage.BUCKET_NAME
    assert f"'{bucket}'" in sql
    assert "public = false" in sql
    assert "file_size_limit" in sql
    assert "10485760" in sql
    assert "application/pdf" in sql


def test_document_storage_policies_scope_every_operation_to_auth_user():
    sql = SCHEMA.read_text(encoding="utf-8")
    assert 'for select to authenticated' in sql
    assert 'for insert to authenticated' in sql
    assert 'for delete to authenticated' in sql
    assert sql.count("(select auth.uid())::text") >= 3
    assert sql.count("bucket_id = 'sowia-private-documents'") >= 3


def test_cloud_memory_and_history_tables_have_rls_enabled():
    sql = SCHEMA.read_text(encoding="utf-8")
    for table in ("sowia_memory_items", "sowia_messages"):
        assert f"alter table public.{table} enable row level security" in sql
        assert f"using ((select auth.uid()) = user_id)" in sql
        assert f"with check ((select auth.uid()) = user_id)" in sql

"""Ensure the Supabase Storage diagnostic stays read-only and scoped."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SQL = (ROOT / "supabase_storage_diagnostics.sql").read_text(encoding="utf-8").lower()


def test_storage_diagnostic_reads_only_expected_bucket_and_policy_catalog():
    assert "from storage.buckets" in SQL
    assert "where id = 'sowia-files'" in SQL
    assert "from pg_policies" in SQL
    assert "schemaname = 'storage'" in SQL
    assert "tablename = 'objects'" in SQL


def test_storage_diagnostic_contains_no_mutating_sql_statements():
    statements = re.sub(r"--[^\\n]*", "", SQL)
    statements = re.sub(r"'(?:''|[^'])*'", "''", statements)
    assert not re.search(r"\\b(insert|update|delete|drop|create|alter|truncate|grant|revoke)\\b", statements)

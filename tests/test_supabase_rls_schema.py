"""Regression tests for Supabase row-level security SQL policies."""

from pathlib import Path
import re

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = {
    "sowia_messages": ROOT / "supabase" / "schema.sql",
    "sowia_memory_items": ROOT / "supabase" / "schema.sql",
    "sowia_documents": ROOT / "supabase" / "document_library.sql",
}


@pytest.mark.parametrize("table_name,schema_path", SCHEMAS.items())
def test_private_table_has_row_level_security_enabled(table_name, schema_path):
    sql = schema_path.read_text(encoding="utf-8")
    assert re.search(
        rf"alter\s+table\s+(?:public\.)?{table_name}\s+enable\s+row\s+level\s+security",
        sql,
        re.IGNORECASE,
    )


@pytest.mark.parametrize("table_name,schema_path", SCHEMAS.items())
def test_private_table_has_authenticated_owner_policies(table_name, schema_path):
    sql = schema_path.read_text(encoding="utf-8")
    policies = re.findall(
        rf"create\s+policy\s+.*?on\s+(?:public\.)?{table_name}\s+for\s+(select|insert|delete)\s+to\s+authenticated(.*?);",
        sql,
        re.IGNORECASE | re.DOTALL,
    )
    commands = {command.lower() for command, _ in policies}
    assert {"select", "insert", "delete"} <= commands

    for command, policy_body in policies:
        if command.lower() in {"select", "delete"}:
            assert re.search(r"using\s*\(.*?auth\.uid\(\).*?user_id", policy_body, re.IGNORECASE | re.DOTALL)
        if command.lower() == "insert":
            assert re.search(r"with\s+check\s*\(.*?auth\.uid\(\).*?user_id", policy_body, re.IGNORECASE | re.DOTALL)

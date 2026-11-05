"""Static regression checks for private Supabase memory and chat tables."""
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = (ROOT / "supabase_schema.sql").read_text(encoding="utf-8").lower()
VERIFIER = (ROOT / "supabase" / "verify_security.sql").read_text(encoding="utf-8").lower()


def _policy_blocks(sql):
    return re.findall(
        r"create\s+policy\s+.*?\s+on\s+public\.(\w+)(.*?);",
        sql,
        flags=re.IGNORECASE | re.DOTALL,
    )


def test_private_tables_have_row_level_security_enabled():
    for table in ("sowia_memory_items", "sowia_messages"):
        assert re.search(
            rf"alter\s+table\s+public\.{table}\s+enable\s+row\s+level\s+security",
            SCHEMA,
        )


def test_every_memory_and_message_policy_is_bound_to_authenticated_owner():
    policies = [
        (table, block)
        for table, block in _policy_blocks(SCHEMA)
        if table in {"sowia_memory_items", "sowia_messages"}
    ]
    assert len(policies) == 6

    for table, block in policies:
        assert "to authenticated" in block
        assert "auth.uid()" in block
        assert "user_id" in block
        assert "to anon" not in block


def test_private_tables_grant_only_required_operations_to_authenticated_role():
    for table in ("sowia_memory_items", "sowia_messages"):
        assert re.search(
            rf"grant\s+select\s*,\s*insert\s*,\s*delete\s+on\s+public\.{table}\s+to\s+authenticated",
            SCHEMA,
        )
        assert not re.search(
            rf"grant\s+.*\s+on\s+public\.{table}\s+to\s+anon",
            SCHEMA,
        )


def test_read_only_verifier_checks_all_private_table_operations():
    for table in ("sowia_memory_items", "sowia_messages"):
        assert f"('{table}', 'select')" in VERIFIER
        assert f"('{table}', 'insert')" in VERIFIER
        assert f"('{table}', 'delete')" in VERIFIER
    assert "auth.uid()" in VERIFIER
    assert "user_id" in VERIFIER

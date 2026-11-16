"""Static regression guards for the workspace RLS migration.

These checks do not replace live two-account Supabase RLS tests. They ensure
that future edits do not silently remove either half of the access predicate.
"""
from pathlib import Path
import re

MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "supabase"
    / "migrations"
    / "20261116150000_harden_workspace_rls_owner_isolation.sql"
)


def _policy(table: str, operation: str) -> str:
    sql = MIGRATION.read_text(encoding="utf-8")
    match = re.search(
        rf"create\s+policy\s+{table}_{operation}_own\b(.*?);",
        sql,
        flags=re.IGNORECASE | re.DOTALL,
    )
    assert match, f"Politique absente : {table}_{operation}_own"
    return match.group(1).lower()


def _assert_owner_and_workspace_gate(policy_sql: str) -> None:
    assert "auth.uid()" in policy_sql
    assert "user_id" in policy_sql
    assert "workspace_id = 'personal'" in policy_sql
    assert "sowia_has_professional_access()" in policy_sql


def test_all_message_operations_require_owner_and_workspace_access():
    for operation in ("select", "insert", "update", "delete"):
        _assert_owner_and_workspace_gate(_policy("messages", operation))


def test_all_memory_operations_require_owner_and_workspace_access():
    for operation in ("select", "insert", "update", "delete"):
        _assert_owner_and_workspace_gate(_policy("memory", operation))


def test_update_policies_check_both_old_and_new_row():
    for table in ("messages", "memory"):
        sql = _policy(table, "update")
        assert "using (" in sql
        assert "with check (" in sql


def test_legacy_permissive_premium_policies_are_removed():
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    assert 'drop policy if exists "require premium for professional messages"' in sql
    assert 'drop policy if exists "require premium for professional memories"' in sql

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

def test_professional_access_helper_is_invoker_and_requires_authenticated_owner():
    sql = (
        Path(__file__).resolve().parents[1]
        / "supabase"
        / "migrations"
        / "20261113000100_sowia_professional_access_gate.sql"
    ).read_text(encoding="utf-8").lower()
    assert "security invoker" in sql
    assert "current_user_id := (select auth.uid())" in sql
    assert "if current_user_id is null then" in sql
    assert "return false" in sql
    assert "entitlement.user_id = $1" in sql
    assert "entitlement.status = ''active''" in sql
    assert "subscription.user_id = $1" in sql


def test_two_account_live_test_is_locked_to_dedicated_project_and_uses_user_jwts():
    integration = (
        Path(__file__).resolve().parents[1]
        / "tests"
        / "integration"
        / "test_supabase_two_user_isolation.py"
    ).read_text(encoding="utf-8")
    assert "mrbmoavotzcuzvnhfjla.supabase.co" in integration
    assert "SOWIA_TEST_USER_A_EMAIL" in integration
    assert "SOWIA_TEST_USER_B_EMAIL" in integration
    assert "assert account_a.user_id != account_b.user_id" in integration
    assert "service_role" in integration
    assert "allow_redirects=False" in integration


def test_manual_professional_gate_check_is_transactional_and_covers_all_workspace_tables():
    manual = (
        Path(__file__).resolve().parents[1]
        / "tests"
        / "integration"
        / "manual_professional_gate_two_account.sql"
    ).read_text(encoding="utf-8").lower()
    assert manual.strip().startswith("-- manual no-third-email")
    assert "begin;" in manual
    assert "rollback;" in manual
    assert manual.index("rollback;") > manual.index("select 'pass:")
    assert "set local role authenticated" in manual
    assert "sowia_has_professional_access()" in manual
    for table in ("sowia_messages", "sowia_memory_items", "sowia_projects"):
        assert f"insert into public.{table}" in manual
    assert "professional" in manual
    assert "personal" in manual

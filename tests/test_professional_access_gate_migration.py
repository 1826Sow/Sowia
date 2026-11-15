"""Static regression checks for the database-enforced Professional workspace gate.

These checks complement (but do not replace) the dedicated-project live RLS test.
"""
from pathlib import Path
import re


MIGRATION = Path(
    "supabase/migrations/20261115000100_sowia_professional_access_gate.sql"
)
STORAGE_POLICIES = Path("supabase_storage_policies.sql")


def _policy_block(sql: str, policy_name: str) -> str:
    match = re.search(
        rf'create\\s+policy\\s+"{re.escape(policy_name)}".*?;',
        sql,
        flags=re.IGNORECASE | re.DOTALL,
    )
    assert match, f"Missing RLS policy: {policy_name}"
    return match.group(0).lower()


def test_professional_access_function_is_invoker_scoped_and_not_public():
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    function = sql.split("$function$", 2)[1]

    assert "security invoker" in sql
    assert "set search_path = ''" in sql
    assert "auth.uid()" in function
    assert "entitlement.plan = 'premium'" in function
    assert "entitlement.status = 'active'" in function
    assert "entitlement.provider = 'paypal'" in function
    assert "subscription.status = ''active''" in function
    assert "subscription.provider = ''paypal''" in function
    assert "to_regclass('public.sowia_subscriptions')" in function
    assert "execute" in function
    assert "revoke all on function public.sowia_has_professional_access() from public" in sql
    assert "revoke all on function public.sowia_has_professional_access() from anon" in sql
    assert "grant execute on function public.sowia_has_professional_access() to authenticated" in sql
    assert "grant select on public.sowia_entitlements to authenticated" in sql
    assert "security definer" not in sql


def test_optional_subscription_table_is_not_required_by_migration():
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    assert "if to_regclass('public.sowia_subscriptions') is not null then" in sql
    assert "execute 'grant select on public.sowia_subscriptions to authenticated'" in sql
    assert "grant select on public.sowia_subscriptions to authenticated;" not in sql


def test_messages_and_memory_gate_every_existing_operation():
    expected = {
        "Users can read own messages": "for select",
        "Users can add own messages": "for insert",
        "Users can delete own messages": "for delete",
        "Users can read own memory": "for select",
        "Users can add own memory": "for insert",
        "Users can delete own memory": "for delete",
    }
    sql = MIGRATION.read_text(encoding="utf-8")

    for name, operation in expected.items():
        block = _policy_block(sql, name)
        assert operation in block, f"{name} must remain a {operation} policy"
        assert "workspace_id = 'personal'" in block, (
            f"{name} must preserve the Personal workspace"
        )
        assert "public.sowia_has_professional_access()" in block, (
            f"{name} must enforce Premium for Professional rows"
        )
        assert "auth.uid()" in block, f"{name} must enforce row ownership"


def test_storage_policies_enforce_the_professional_premium_gate():
    sql = STORAGE_POLICIES.read_text(encoding="utf-8").lower()
    expected = {
        "SOW IA users can read own workspace PDFs": "for select",
        "SOW IA users can upload own workspace PDFs": "for insert",
        "SOW IA users can delete own workspace PDFs": "for delete",
    }

    for name, operation in expected.items():
        block = _policy_block(sql, name)
        assert operation in block
        assert "public.sowia_has_professional_access()" in block, (
            f"{name} must enforce Premium for Professional PDFs"
        )
        assert "'personal'" in block and "'professional'" in block

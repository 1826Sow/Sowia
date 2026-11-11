"""Static security guards for Premium enforcement on Professional workspace rows."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = (
    ROOT / "supabase/migrations/20261111000200_sowia_professional_workspace_rls.sql"
).read_text(encoding="utf-8").lower()


def test_migration_adds_workspace_columns_and_constraints_without_data_loss():
    normalized = " ".join(MIGRATION.split())
    for table in ("sowia_memory_items", "sowia_messages"):
        assert (
            f"alter table public.{table} add column if not exists "
            "workspace_id text not null default 'personal'"
        ) in normalized
        assert f"add constraint {table}_workspace_id_check" in normalized
    assert "drop table" not in MIGRATION
    assert "delete from public.sowia_memory_items" not in MIGRATION
    assert "delete from public.sowia_messages" not in MIGRATION


def test_professional_access_function_is_fail_closed_and_search_path_is_empty():
    normalized = " ".join(MIGRATION.split())
    assert "security definer" in normalized
    assert "set search_path = ''" in normalized
    assert "current_user_id := (select auth.uid())" in normalized
    assert "if current_user_id is null then" in normalized
    assert "revoke all on function public.sowia_has_professional_access() from public, anon" in normalized
    assert "grant execute on function public.sowia_has_professional_access() to authenticated" in normalized


def test_professional_access_accepts_one_time_and_recurring_active_paypal_entitlements():
    normalized = " ".join(MIGRATION.split())
    assert "from public.sowia_entitlements as entitlement" in normalized
    assert "entitlement.status = 'active'" in normalized
    assert "entitlement.provider = 'paypal'" in normalized
    assert "to_regclass('public.sowia_subscriptions') is not null" in normalized
    assert "from public.sowia_subscriptions as subscription" in normalized
    assert "subscription.status = ''active''" in normalized
    assert "subscription.provider = ''paypal''" in normalized


def test_workspace_guards_are_restrictive_and_preserve_personal_access():
    normalized = " ".join(MIGRATION.split())
    for table, policy in (
        ("sowia_memory_items", "Require Premium for Professional memories"),
        ("sowia_messages", "Require Premium for Professional messages"),
    ):
        assert f'drop policy if exists "{policy.lower()}"' in normalized
        assert f'on public.{table}' in normalized
    assert normalized.count("as restrictive for all to authenticated") == 2
    assert normalized.count("workspace_id = 'personal'") == 4
    assert normalized.count("or public.sowia_has_professional_access()") == 4


def test_migration_does_not_delete_or_rewrite_existing_user_data():
    assert "delete from public.sowia_memory_items" not in MIGRATION
    assert "delete from public.sowia_messages" not in MIGRATION
    assert "truncate " not in MIGRATION
    assert "drop table" not in MIGRATION

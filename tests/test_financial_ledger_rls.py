"""Regression checks for the financial ledger's database access boundary."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEDGER_MIGRATION = ROOT / "supabase/migrations/20261110000100_sowia_financial_ledger.sql"
SUBSCRIPTION_MIGRATION = ROOT / "supabase/migrations/20261111000100_paypal_billing_ledger_link.sql"


def test_financial_ledger_enforces_owner_scoped_read_only_access():
    sql = LEDGER_MIGRATION.read_text(encoding="utf-8").lower()

    assert "alter table public.sowia_financial_transactions enable row level security" in sql
    assert "for select to authenticated" in sql
    assert "using ((select auth.uid()) = user_id)" in sql
    assert "revoke all on public.sowia_financial_transactions from anon, authenticated" in sql
    assert "grant select on public.sowia_financial_transactions to authenticated" in sql

    # Authenticated clients must never receive direct write privileges.
    assert "grant insert on public.sowia_financial_transactions to authenticated" not in sql
    assert "grant update on public.sowia_financial_transactions to authenticated" not in sql
    assert "grant delete on public.sowia_financial_transactions to authenticated" not in sql


def test_paypal_subscription_link_migration_does_not_weaken_ledger_security():
    sql = SUBSCRIPTION_MIGRATION.read_text(encoding="utf-8").lower()

    assert "add column if not exists paypal_subscription_id text" in sql
    assert "create index if not exists sowia_financial_transactions_paypal_subscription_idx" in sql
    assert "enable row level security" not in sql
    assert "disable row level security" not in sql
    assert "grant " not in sql
    assert "revoke " not in sql


def test_paypal_refund_trigger_uses_empty_search_path_and_is_not_definer():
    sql = LEDGER_MIGRATION.read_text(encoding="utf-8").lower()
    function_start = sql.index(
        "create or replace function public.sowia_enforce_paypal_refund_capture_limit()"
    )
    function_end = sql.index("$$;", sql.index("as $$", function_start)) + 3
    function_sql = sql[function_start:function_end]

    assert "set search_path = ''" in function_sql
    assert "security definer" not in function_sql
    assert "from public.sowia_financial_transactions" in function_sql
    assert "update on public.sowia_financial_transactions to authenticated" not in sql
    assert "insert on public.sowia_financial_transactions to authenticated" not in sql

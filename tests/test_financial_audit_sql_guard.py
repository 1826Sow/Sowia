"""Static security regression checks for the immutable financial audit migration.

These checks inspect SQL source; they do not replace PostgreSQL/Supabase integration tests.
"""

from pathlib import Path


MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "supabase"
    / "migrations"
    / "20261110000300_sowia_financial_audit_log.sql"
)


def migration_sql():
    return MIGRATION.read_text(encoding="utf-8").lower()


def test_audit_log_is_created_with_rls_and_server_only_read_access():
    sql = migration_sql()
    assert "create table if not exists public.sowia_financial_audit_log" in sql
    assert "alter table public.sowia_financial_audit_log enable row level security" in sql
    assert (
        "revoke all on public.sowia_financial_audit_log "
        "from public, anon, authenticated, service_role"
    ) in sql
    assert "grant select on public.sowia_financial_audit_log to service_role" in sql
    assert "grant insert" not in sql
    assert "grant update" not in sql
    assert "grant delete" not in sql


def test_audit_rows_are_immutable_at_database_level():
    sql = migration_sql()
    assert "create or replace function public.sowia_prevent_financial_audit_mutation()" in sql
    assert "sowia financial audit records are immutable" in sql
    assert "before update or delete on public.sowia_financial_audit_log" in sql
    assert "execute function public.sowia_prevent_financial_audit_mutation()" in sql


def test_ledger_changes_are_captured_by_security_definer_trigger():
    sql = migration_sql()
    assert "create or replace function public.sowia_audit_financial_ledger_change()" in sql
    assert "security definer" in sql
    assert "after insert or update or delete on public.sowia_financial_transactions" in sql
    assert "execute function public.sowia_audit_financial_ledger_change()" in sql
    assert "auth.uid()" in sql
    assert "tg_op" in sql
    assert "txid_current()" in sql


def test_audit_snapshots_include_financial_fields_but_not_credentials():
    sql = migration_sql()
    for field in (
        "'provider_payment_id'",
        "'transaction_type'",
        "'status'",
        "'gross_amount'",
        "'gross_currency'",
        "'fee_amount'",
        "'net_amount'",
    ):
        assert field in sql
    for forbidden in ("client_secret", "access_token", "refresh_token", "webhook_secret"):
        assert forbidden not in sql

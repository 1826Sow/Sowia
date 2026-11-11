"""Static guardrails for the FINAL TEC audit vault SQL proposal."""
from pathlib import Path

SQL = Path("supabase/proposals/final_tec_audit_vault.sql").read_text(encoding="utf-8")


def test_vault_is_in_private_schema_and_rls_is_forced():
    assert "create schema if not exists final_tec_private" in SQL.lower()
    assert "enable row level security" in SQL.lower()
    assert "force row level security" in SQL.lower()


def test_client_roles_receive_no_table_privileges():
    lowered = SQL.lower()
    assert "revoke all on final_tec_private.audit_events from public, anon, authenticated" in lowered
    assert "grant select, insert on final_tec_private.audit_events to service_role" in lowered
    assert "grant select, insert, update, delete" not in lowered


def test_append_only_and_server_generated_chain_controls_exist():
    lowered = SQL.lower()
    assert "before insert on final_tec_private.audit_events" in lowered
    assert "before update or delete" in lowered
    assert "before truncate" in lowered
    assert "pg_advisory_xact_lock" in lowered
    assert "extensions.digest" in lowered


def test_no_client_policy_or_production_migration_claim():
    lowered = SQL.lower()
    assert "create policy" not in lowered
    assert "proposal only" in lowered
    assert "has not been executed" in lowered

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


def test_sequence_number_is_allocated_after_chain_lock():
    lowered = SQL.lower()
    assert "create sequence if not exists final_tec_private.audit_events_sequence_id_seq" in lowered
    assert "sequence_id bigint primary key" in lowered
    assert "generated always as identity" not in lowered
    lock = lowered.index("perform pg_advisory_xact_lock(184631, 202611)")
    allocate = lowered.index("new.sequence_id := nextval('")
    prior = lowered.index("select event_hash", allocate)
    assert lock < allocate < prior


def test_security_definer_rpc_uses_restricted_search_path():
    lowered = SQL.lower()
    assert "set search_path = pg_catalog, auth, final_tec_private" in lowered
    assert "set search_path = pg_catalog, public, final_tec_private, auth" not in lowered


def test_sql_contract_includes_view_event_and_allowed_outcome():
    lowered = SQL.lower()
    assert "'investor_dashboard_viewed'" in lowered
    assert "'allowed'" in lowered

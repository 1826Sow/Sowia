from pathlib import Path


MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "supabase/migrations/20261111000700_paypal_one_time_entitlement_atomic.sql"
).read_text(encoding="utf-8").lower()


def test_one_time_paypal_rpc_is_transactional_and_service_role_only():
    normalized = " ".join(MIGRATION.split())
    assert normalized.startswith("-- atomically")
    assert "begin;" in normalized
    assert "commit;" in normalized
    assert "security definer" in normalized
    assert "set search_path = ''" in normalized
    assert "to service_role" in normalized
    assert "from public, anon, authenticated" in normalized


def test_one_time_paypal_rpc_writes_ledger_and_entitlement_in_one_function():
    assert "insert into public.sowia_financial_transactions" in MIGRATION
    assert "insert into public.sowia_entitlements" in MIGRATION
    assert "pg_advisory_xact_lock" in MIGRATION
    assert "on conflict (provider, provider_payment_id, transaction_type) do nothing" in MIGRATION


def test_one_time_paypal_replay_cannot_regrant_stale_entitlement():
    assert "v_entitlement_order_id = p_order_id and v_entitlement_status = 'active'" in MIGRATION
    assert "return 'replay_ignored'" in MIGRATION
    assert "return 'already_granted'" in MIGRATION

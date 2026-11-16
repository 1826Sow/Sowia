"""Regression checks for atomic, fail-closed PayPal webhook ordering."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEBHOOK = (ROOT / "supabase/functions/paypal-webhook/index.ts").read_text(
    encoding="utf-8"
)
MIGRATION = (
    ROOT
    / "supabase/migrations/20261116150000_paypal_block_event_chronology.sql"
).read_text(encoding="utf-8")


def test_webhook_applies_subscription_state_through_atomic_database_function():
    assert "/rest/v1/rpc/sowia_apply_paypal_subscription_event" in WEBHOOK
    assert "p_event_created_at: eventCreatedAt" in WEBHOOK
    assert "p_blocked_event: blockedEvent" in WEBHOOK
    assert "Unable to atomically apply PayPal subscription event" in WEBHOOK


def test_database_serializes_decisions_per_subscription_before_reading_state():
    lock = MIGRATION.index("pg_catalog.pg_advisory_xact_lock")
    block_read = MIGRATION.index("from public.sowia_paypal_subscription_blocks")
    subscription_read = MIGRATION.index("from public.sowia_subscriptions")
    assert lock < block_read < subscription_read


def test_stale_and_legacy_block_records_fail_closed():
    assert "v_block.source_event_created_at is null" in MIGRATION
    assert "p_event_created_at <= v_block.source_event_created_at" in MIGRATION
    assert "((v_previously_blocked or v_has_block) and not v_can_recover)" in MIGRATION


def test_recovery_requires_a_later_matching_event_and_active_subscription():
    assert "p_event_created_at > v_block.source_event_created_at" in MIGRATION
    assert "p_event_type = 'PAYMENT.SALE.COMPLETED'" in MIGRATION
    assert "p_event_type = 'BILLING.SUBSCRIPTION.ACTIVATED'" in MIGRATION
    assert "upper(coalesce(p_status, 'UNKNOWN')) <> 'ACTIVE'" in MIGRATION


def test_rpc_is_not_executable_by_end_user_roles():
    assert "revoke all on function public.sowia_apply_paypal_subscription_event" in MIGRATION
    assert "from public, anon, authenticated" in MIGRATION
    assert "to service_role" in MIGRATION

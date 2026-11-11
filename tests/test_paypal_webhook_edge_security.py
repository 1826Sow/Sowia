"""Static security guards for the PayPal Edge webhook trust boundary."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEBHOOK = (ROOT / "supabase/functions/paypal-webhook/index.ts").read_text(encoding="utf-8")
CONFIG = (ROOT / "supabase/config.toml").read_text(encoding="utf-8")


def test_paypal_webhook_requires_paypal_signature_before_subscription_write():
    source = WEBHOOK
    verify = source.index("const verified = await verifyWebhook(")
    reject = source.index('if (!verified) return json(', verify)
    write = source.index('"/rest/v1/rpc/sowia_reconcile_paypal_subscription"', reject)
    assert verify < reject < write
    assert 'verification_status === "SUCCESS"' in source


def test_paypal_webhook_reconciles_subscription_owner_and_plan_with_paypal():
    source = WEBHOOK
    assert 'baseUrl + "/v1/billing/subscriptions/"' in source
    assert "subscription.id !== subscriptionId" in source
    assert "subscription.plan_id !== planId" in source
    assert "uuidPattern.test(userId)" in source
    assert "user_id: userId" in source


def test_paypal_webhook_endpoint_disables_supabase_jwt_only_for_signed_paypal_events():
    assert "[functions.paypal-webhook]" in CONFIG
    assert "verify_jwt = false" in CONFIG
    assert "paypal-transmission-sig" in WEBHOOK
    assert "verify-webhook-signature" in WEBHOOK

def test_paypal_webhook_rejects_unknown_subscription_status_before_persistence():
    status_check = WEBHOOK.index("const allowedStatuses = new Set([")
    reject = WEBHOOK.index('if (!allowedStatuses.has(normalizedStatus))', status_check)
    write = WEBHOOK.index('"/rest/v1/rpc/sowia_reconcile_paypal_subscription"', reject)
    assert status_check < reject < write
    for status in ("APPROVAL_PENDING", "APPROVED", "ACTIVE", "SUSPENDED", "CANCELLED", "EXPIRED"):
        assert f'"{status}"' in WEBHOOK
    assert 'p_status: effectiveStatus' in WEBHOOK

def test_paypal_payment_failure_blocks_premium_until_paypal_counter_resets():
    assert '"BILLING.SUBSCRIPTION.PAYMENT.FAILED"' in WEBHOOK
    assert '"BILLING.SUBSCRIPTION.PAYMENT.SUCCEEDED"' in WEBHOOK
    counter = WEBHOOK.index("const failedPaymentsCount = Number(billing.failed_payments_count);")
    validation = WEBHOOK.index("if (!Number.isInteger(failedPaymentsCount)", counter)
    gate = WEBHOOK.index('let effectiveStatus = normalizedStatus === "ACTIVE" && failedPaymentsCount > 0', validation)
    write = WEBHOOK.index('"/rest/v1/rpc/sowia_reconcile_paypal_subscription"', gate)
    assert counter < validation < gate < write
    assert '? "past_due"' in WEBHOOK
    assert "failedPaymentsCount > 0" in WEBHOOK


def test_subscription_refund_or_reversal_uses_atomic_database_reconciliation():
    source = WEBHOOK
    recovery = source.index("const verifiedPaymentRecovery =")
    rpc = source.index('"/rest/v1/rpc/sowia_reconcile_paypal_subscription"', recovery)
    assert recovery < rpc
    migration = (ROOT / "supabase/migrations/20261111000500_paypal_subscription_atomic_reconciliation.sql").read_text(encoding="utf-8")
    assert "'PAYMENT.SALE.REFUNDED'" in migration
    assert "'PAYMENT.SALE.REVERSED'" in migration
    assert "'BILLING.SUBSCRIPTION.PAYMENT.SUCCEEDED'" in migration
    assert "p_recovery_verified: verifiedPaymentRecovery" in source
    assert "p_event_type: eventType" in source
    assert "p_event_time: eventTime" in source
    assert "Date.parse(eventTime)" in source


def test_subscription_reconciliation_rpc_serializes_concurrent_events():
    migration = (ROOT / "supabase/migrations/20261111000500_paypal_subscription_atomic_reconciliation.sql").read_text(encoding="utf-8")
    assert "security definer" in migration.lower()
    assert "set search_path = ''" in migration
    assert "pg_advisory_xact_lock" in migration
    assert "v_existing_user_id <> p_user_id" in migration
    assert "v_existing_plan_id <> p_paypal_plan_id" in migration
    assert "owner or plan is immutable" in migration
    assert "last_webhook_event_time" in migration
    assert "payment_review_at" in migration
    assert "p_event_time < v_existing_event_time" in migration
    assert "p_event_time > v_review_at" in migration
    assert "for update" in migration.lower()
    assert "PAYMENT.SALE.REFUNDED" in migration
    assert "PAYMENT.SALE.REVERSED" in migration
    assert "v_existing_status = 'payment_review'" in migration
    assert "grant execute" in migration.lower()
    assert "to service_role" in migration


def test_one_time_refund_branch_does_not_depend_on_subscription_plan_catalog():
    source = WEBHOOK
    refund_branch = source.index('if (eventType === "PAYMENT.CAPTURE.REFUNDED")')
    catalog = source.index("const catalogResponse = await fetch(")
    assert refund_branch < catalog


def test_one_time_capture_refund_is_verified_and_revokes_only_linked_entitlement():
    source = WEBHOOK
    capture_events = source.index('"PAYMENT.CAPTURE.REFUNDED"')
    handler = source.index('if (eventType === "PAYMENT.CAPTURE.REFUNDED")')
    refund_fetch = source.index("/v2/payments/refunds/", handler)
    refund_status = source.index('refund.status || ""', refund_fetch)
    parent_link = source.index('String(link.rel || "").toLowerCase() === "up"', refund_status)
    capture_fetch = source.index("/v2/payments/captures/", parent_link)
    capture_status = source.index('capture.status || ""', capture_fetch)
    ledger_lookup = source.index("/rest/v1/sowia_financial_transactions", capture_status)
    order_check = source.index("ledger.paypal_order_id !== orderId", ledger_lookup)
    revoke = source.index("/rest/v1/sowia_entitlements?user_id=eq.", order_check)
    write = source.index('method: "PATCH"', revoke)
    assert capture_events < handler < refund_fetch < refund_status < parent_link < capture_fetch < capture_status < ledger_lookup < order_check < revoke < write
    assert 'new Set(["PARTIALLY_REFUNDED", "REFUNDED"])' in source
    assert 'JSON.stringify({ status: "inactive" })' in source
    assert '"return=representation"' in source
    assert "PAYMENT.CAPTURE.REVERSED" in source


def test_terminal_paypal_events_override_a_stale_active_api_snapshot():
    source = WEBHOOK
    status_block = source.index("let effectiveStatus = normalizedStatus")
    cancel = source.index('eventType === "BILLING.SUBSCRIPTION.CANCELLED"', status_block)
    expire = source.index('eventType === "BILLING.SUBSCRIPTION.EXPIRED"', cancel)
    suspend = source.index('eventType === "BILLING.SUBSCRIPTION.SUSPENDED"', expire)
    rpc = source.index('"/rest/v1/rpc/sowia_reconcile_paypal_subscription"', suspend)
    assert status_block < cancel < expire < suspend < rpc
    assert 'effectiveStatus = "cancelled"' in source
    assert 'effectiveStatus = "expired"' in source
    assert 'effectiveStatus = "suspended"' in source


def test_cancelled_and_expired_subscriptions_are_terminal_in_atomic_rpc():
    migration = (ROOT / "supabase/migrations/20261111000500_paypal_subscription_atomic_reconciliation.sql").read_text(encoding="utf-8")
    terminal = migration.index("if v_existing_status in ('cancelled', 'expired') then")
    write = migration.index("insert into public.sowia_subscriptions", terminal)
    assert terminal < write
    assert "return v_existing_status;" in migration[terminal:write]


def test_cancellation_and_expiration_override_payment_review_hold():
    migration = (ROOT / "supabase/migrations/20261111000500_paypal_subscription_atomic_reconciliation.sql").read_text(encoding="utf-8")
    cancel = migration.index("p_event_type = 'BILLING.SUBSCRIPTION.CANCELLED'")
    expire = migration.index("p_event_type = 'BILLING.SUBSCRIPTION.EXPIRED'", cancel)
    suspend = migration.index("p_event_type = 'BILLING.SUBSCRIPTION.SUSPENDED'", expire)
    refund = migration.index("p_event_type in ('PAYMENT.SALE.REFUNDED', 'PAYMENT.SALE.REVERSED')", suspend)
    review_hold = migration.index("v_existing_status = 'payment_review'", refund)
    assert cancel < expire < suspend < refund < review_hold


def test_one_time_refund_is_recorded_once_in_financial_ledger_before_entitlement_revocation():
    source = WEBHOOK
    handler = source.index('if (eventType === "PAYMENT.CAPTURE.REFUNDED")')
    ledger_write = source.index('"/rest/v1/sowia_financial_transactions?on_conflict=provider,provider_payment_id,transaction_type"', handler)
    conflict_ignore = source.index('resolution=ignore-duplicates,return=minimal', ledger_write)
    confirm = source.index("const confirmRefundResponse = await fetch(refundLedgerUrl", conflict_ignore)
    revoke = source.index('"/rest/v1/sowia_entitlements?user_id=eq."', confirm)
    assert handler < ledger_write < conflict_ignore < confirm < revoke
    assert 'transaction_type: "refund"' in source
    assert 'status: "manual_review"' in source
    assert 'parent_capture_id: captureId' in source
    assert 'provider_payment_id: refundId' in source
    assert 'Number(row.gross_amount) === Number(refundAmount.value)' in source
    assert 'String(row.parent_capture_id || "") === captureId' in source


def test_subscription_webhook_deduplicates_exact_paypal_event_ids():
    source = WEBHOOK
    event_time = source.index('const eventTime = String(event.create_time || "").trim();')
    event_id = source.index('const eventId = String(event.id || "").trim();', event_time)
    rpc = source.index("p_event_id: eventId", event_id)
    assert event_time < event_id < rpc
    assert 'eventId.length > 128' in source

    migration = (ROOT / "supabase/migrations/20261111000600_paypal_webhook_event_deduplication.sql").read_text(encoding="utf-8")
    assert "create table if not exists public.sowia_paypal_webhook_events" in migration
    assert "event_id text primary key" in migration
    assert "on conflict (event_id) do nothing" in migration
    assert "v_claimed_event_id is null" in migration
    assert "PayPal webhook event ID conflicts with another event" in migration
    assert "return v_existing_status;" in migration
    assert "drop function if exists public.sowia_reconcile_paypal_subscription(" in migration
    assert "p_event_id text" in migration
    assert "to service_role" in migration


def test_paypal_event_receipt_registry_is_private_and_claimed_atomically():
    migration = (ROOT / "supabase/migrations/20261111000600_paypal_webhook_event_deduplication.sql").read_text(encoding="utf-8")
    lock = migration.index("pg_advisory_xact_lock")
    claim = migration.index("insert into public.sowia_paypal_webhook_events")
    duplicate = migration.index("if v_claimed_event_id is null then", claim)
    chronology = migration.index("p_event_time < v_existing_event_time", duplicate)
    assert lock < claim < duplicate < chronology
    assert "alter table public.sowia_paypal_webhook_events enable row level security" in migration
    assert "revoke all on public.sowia_paypal_webhook_events from public, anon, authenticated" in migration
    assert "event_id text primary key" in migration
    assert "event_type = p_event_type" in migration
    assert "event_time = p_event_time" in migration
    assert "on conflict (event_id) do nothing" in migration


def test_paypal_sale_completion_can_recover_payment_review_with_complete_latest_payment_proof():
    source = WEBHOOK
    recovery = source.index("const verifiedPaymentRecovery =")
    sale_event = source.index('eventType === "PAYMENT.SALE.COMPLETED"', recovery)
    legacy_event = source.index('eventType === "BILLING.SUBSCRIPTION.PAYMENT.SUCCEEDED"', sale_event)
    proof = source.index("if (verifiedPaymentRecovery) {", legacy_event)
    amount = source.index("Number(paymentAmount.value) !== 9.90", proof)
    currency = source.index('String(paymentAmount.currency_code || "").toUpperCase() !== "EUR"', amount)
    payment_time = source.index("!lastPaymentTime || !Number.isFinite(Date.parse(lastPaymentTime))", currency)
    reject = source.index('PayPal recovery payment proof is incomplete', payment_time)
    rpc = source.index('"/rest/v1/rpc/sowia_reconcile_paypal_subscription"', reject)
    assert recovery < sale_event < legacy_event < proof < amount < currency < payment_time < reject < rpc
    assert 'const lastPaymentTime = String(lastPayment.time || "").trim();' in source

    migration = (ROOT / "supabase/migrations/20261111000600_paypal_webhook_event_deduplication.sql").read_text(encoding="utf-8")
    assert "'PAYMENT.SALE.COMPLETED'" in migration
    assert "p_recovery_verified is distinct from" in migration
    assert "p_event_type in (" in migration
    assert "'BILLING.SUBSCRIPTION.PAYMENT.SUCCEEDED'" in migration

def test_one_time_capture_reversal_resolves_verified_refund_parent_and_revokes_entitlement():
    source = WEBHOOK
    event = source.index('"PAYMENT.CAPTURE.REVERSED"')
    handler = source.index('if (eventType === "PAYMENT.CAPTURE.REVERSED")')
    refund_fetch = source.index('/v2/payments/refunds/', handler)
    refund_status = source.index('refund.status || ""', refund_fetch)
    parent_link = source.index('String(link.rel || "").toLowerCase() === "up"', refund_status)
    capture_fetch = source.index('/v2/payments/captures/', parent_link)
    capture_status = source.index('capture.status || ""', capture_fetch)
    ledger_lookup = source.index('transaction_type=eq.payment', capture_status)
    reversal_ledger = source.index('encodeURIComponent(refundId)', ledger_lookup)
    entitlement_revoke = source.index('/rest/v1/sowia_entitlements?user_id=eq.', reversal_ledger)
    assert event < handler < refund_fetch < refund_status < parent_link < capture_fetch < capture_status < ledger_lookup < reversal_ledger < entitlement_revoke
    assert 'parentUrl.origin === new URL(baseUrl).origin' in source
    assert 'captureMatch[1]' in source
    assert 'Number(refundAmount.value) > Number(captureAmount.value)' in source
    assert 'gross_amount: Number(refundAmount.value)' in source
    assert 'provider_payment_id: refundId' in source
    assert 'new Set(["COMPLETED", "PARTIALLY_REFUNDED", "REFUNDED"])' in source
    assert 'status: "manual_review"' in source[reversal_ledger:entitlement_revoke]
    assert 'resolution=ignore-duplicates,return=minimal' in source[reversal_ledger:entitlement_revoke]
    assert 'capture_reversed: true' in source[entitlement_revoke:]

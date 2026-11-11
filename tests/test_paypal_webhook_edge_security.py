"""Static security guards for the PayPal Edge webhook trust boundary."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEBHOOK = (ROOT / "supabase/functions/paypal-webhook/index.ts").read_text(encoding="utf-8")
CONFIG = (ROOT / "supabase/config.toml").read_text(encoding="utf-8")


def test_paypal_webhook_requires_paypal_signature_before_subscription_write():
    source = WEBHOOK
    verify = source.index("const verified = await verifyWebhook(")
    reject = source.index('if (!verified) return json(', verify)
    write = source.index('"/rest/v1/sowia_subscriptions?on_conflict=paypal_subscription_id"', reject)
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
    write = WEBHOOK.index('"/rest/v1/sowia_subscriptions?on_conflict=paypal_subscription_id"', reject)
    assert status_check < reject < write
    for status in ("APPROVAL_PENDING", "APPROVED", "ACTIVE", "SUSPENDED", "CANCELLED", "EXPIRED"):
        assert f'"{status}"' in WEBHOOK
    assert 'status: effectiveStatus' in WEBHOOK

def test_paypal_payment_failure_blocks_premium_until_paypal_counter_resets():
    assert '"BILLING.SUBSCRIPTION.PAYMENT.FAILED"' in WEBHOOK
    assert '"BILLING.SUBSCRIPTION.PAYMENT.SUCCEEDED"' in WEBHOOK
    counter = WEBHOOK.index("const failedPaymentsCount = Number(billing.failed_payments_count);")
    validation = WEBHOOK.index("if (!Number.isInteger(failedPaymentsCount)", counter)
    gate = WEBHOOK.index('let effectiveStatus = normalizedStatus === "ACTIVE" && failedPaymentsCount > 0', validation)
    write = WEBHOOK.index('"/rest/v1/sowia_subscriptions?on_conflict=paypal_subscription_id"', gate)
    assert counter < validation < gate < write
    assert '? "past_due"' in WEBHOOK
    assert "failedPaymentsCount > 0" in WEBHOOK


def test_subscription_refund_or_reversal_blocks_premium_until_verified_successful_payment():
    source = WEBHOOK
    refund_gate = source.index("const isRefundOrReversal =")
    existing_state = source.index('"&select=status&limit=1"', refund_gate)
    recovery = source.index("const verifiedPaymentRecovery =", existing_state)
    hold = source.index('effectiveStatus = "payment_review"', recovery)
    write = source.index('"/rest/v1/sowia_subscriptions?on_conflict=paypal_subscription_id"', hold)
    assert refund_gate < existing_state < recovery < hold < write
    assert 'eventType === "PAYMENT.SALE.REFUNDED"' in source
    assert 'eventType === "PAYMENT.SALE.REVERSED"' in source
    assert 'eventType === "BILLING.SUBSCRIPTION.PAYMENT.SUCCEEDED"' in source
    assert "paymentReviewAlreadyActive && !verifiedPaymentRecovery" in source
    assert 'effectiveStatus = "payment_review"' in source


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
    assert "PAYMENT.CAPTURE.REVERSED" not in source

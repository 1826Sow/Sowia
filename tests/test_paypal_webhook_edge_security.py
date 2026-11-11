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
    assert 'status: normalizedStatus.toLowerCase()' in WEBHOOK

def test_paypal_payment_failure_blocks_premium_until_paypal_counter_resets():
    assert '"BILLING.SUBSCRIPTION.PAYMENT.FAILED"' in WEBHOOK
    assert '"BILLING.SUBSCRIPTION.PAYMENT.SUCCEEDED"' in WEBHOOK
    counter = WEBHOOK.index("const failedPaymentsCount = Number(billing.failed_payments_count);")
    validation = WEBHOOK.index("if (!Number.isInteger(failedPaymentsCount)", counter)
    gate = WEBHOOK.index('const effectiveStatus = normalizedStatus === "ACTIVE" && failedPaymentsCount > 0', validation)
    write = WEBHOOK.index('"/rest/v1/sowia_subscriptions?on_conflict=paypal_subscription_id"', gate)
    assert counter < validation < gate < write
    assert '? "past_due"' in WEBHOOK
    assert "failedPaymentsCount > 0" in WEBHOOK

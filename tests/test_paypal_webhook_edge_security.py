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

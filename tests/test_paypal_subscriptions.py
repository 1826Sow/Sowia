"""Unit tests for the isolated PayPal recurring-subscription helpers."""
import paypal_subscriptions as paypal


def test_subscriptions_are_disabled_by_default(monkeypatch):
    monkeypatch.setattr(paypal, "_setting", lambda name, default="": default)
    assert paypal.paypal_subscription_configuration() is None


def test_enabled_but_incomplete_configuration_fails_closed(monkeypatch):
    values = {
        "SOWIA_SUBSCRIPTIONS_ENABLED": "true",
        "PAYPAL_CLIENT_ID": "client",
        "PAYPAL_CLIENT_SECRET": "secret",
        "PAYPAL_PREMIUM_PLAN_ID": "P-123",
        "PAYPAL_MODE": "sandbox",
        "PAYPAL_SUBSCRIPTION_RETURN_URL": "https://example.com/return",
        "PAYPAL_SUBSCRIPTION_CANCEL_URL": "https://example.com/cancel",
        # Missing webhook ID must prevent activation.
    }
    monkeypatch.setattr(paypal, "_setting", lambda name, default="": values.get(name, default))
    assert paypal.paypal_subscription_configuration() is None


def test_live_mode_requires_https_return_urls(monkeypatch):
    values = {
        "SOWIA_SUBSCRIPTIONS_ENABLED": "true",
        "PAYPAL_CLIENT_ID": "client",
        "PAYPAL_CLIENT_SECRET": "secret",
        "PAYPAL_PREMIUM_PLAN_ID": "P-123",
        "PAYPAL_MODE": "live",
        "PAYPAL_SUBSCRIPTION_RETURN_URL": "http://example.com/return",
        "PAYPAL_SUBSCRIPTION_CANCEL_URL": "https://example.com/cancel",
        "PAYPAL_SUBSCRIPTION_WEBHOOK_ID": "WH-123",
    }
    monkeypatch.setattr(paypal, "_setting", lambda name, default="": values.get(name, default))
    try:
        paypal.paypal_subscription_configuration()
    except ValueError as exc:
        assert "HTTPS" in str(exc)
    else:
        raise AssertionError("HTTP return URL should be rejected")


def test_subscription_id_validation_rejects_untrusted_input(monkeypatch):
    monkeypatch.setattr(paypal, "paypal_subscription_configuration", lambda: {
        "base_url": "https://api-m.sandbox.paypal.com",
        "client_id": "client",
        "client_secret": "secret",
    })
    monkeypatch.setattr(paypal, "_access_token", lambda config: "token")
    called = []
    monkeypatch.setattr(paypal.requests, "get", lambda *args, **kwargs: called.append(args))
    try:
        paypal.get_premium_subscription("../not-an-id")
    except ValueError as exc:
        assert "invalide" in str(exc)
    else:
        raise AssertionError("Invalid subscription ID should be rejected")
    assert called == []


def test_webhook_verification_requires_all_paypal_headers(monkeypatch):
    monkeypatch.setattr(paypal, "paypal_subscription_configuration", lambda: {
        "webhook_id": "WH-123",
        "base_url": "https://api-m.sandbox.paypal.com",
    })
    monkeypatch.setattr(paypal, "_access_token", lambda config: "token")
    called = []
    monkeypatch.setattr(paypal.requests, "post", lambda *args, **kwargs: called.append(args))
    assert paypal.verify_paypal_subscription_webhook(
        {"id": "EVENT-1"}, {"paypal-transmission-id": "only-one-header"}
    ) is False
    assert called == []

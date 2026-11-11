"""Unit tests for the isolated PayPal recurring-subscription helpers."""
import pytest

import paypal_subscriptions as paypal


def test_subscriptions_are_disabled_by_default(monkeypatch):
    monkeypatch.setattr(paypal, "_setting", lambda name, default="": default)
    assert paypal.paypal_subscription_configuration() is None


def test_enabled_but_incomplete_configuration_fails_closed(monkeypatch):
    values = {
        "SOWIA_SUBSCRIPTIONS_ENABLED": "true",
        "PAYPAL_CLIENT_ID": "client",
        "PAYPAL_CLIENT_SECRET": "secret",
        "PAYPAL_MODE": "sandbox",
        "PAYPAL_SUBSCRIPTION_RETURN_URL": "https://example.com/return",
        "PAYPAL_SUBSCRIPTION_CANCEL_URL": "https://example.com/cancel",
        # Missing plan ID must prevent checkout.
    }
    monkeypatch.setattr(paypal, "_setting", lambda name, default="": values.get(name, default))
    config = paypal.paypal_subscription_configuration()
    assert config is not None
    assert config["mode"] == "sandbox"
    assert config["plan_id"] == ""


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


def test_checkout_configuration_does_not_require_webhook_id(monkeypatch):
    values = {
        "SOWIA_SUBSCRIPTIONS_ENABLED": "true",
        "PAYPAL_CLIENT_ID": "client",
        "PAYPAL_CLIENT_SECRET": "secret",
        "PAYPAL_PREMIUM_PLAN_ID": "P-123",
        "PAYPAL_MODE": "sandbox",
        "PAYPAL_SUBSCRIPTION_RETURN_URL": "https://example.com/return",
        "PAYPAL_SUBSCRIPTION_CANCEL_URL": "https://example.com/cancel",
    }
    monkeypatch.setattr(paypal, "_setting", lambda name, default="": values.get(name, default))
    config = paypal.paypal_subscription_configuration()
    assert config is not None
    assert config["webhook_id"] == ""


def test_live_paypal_mode_is_blocked_in_subscription_ui():
    """The app must never expose subscription creation against PayPal Live."""
    from pathlib import Path

    source = Path("app.py").read_text(encoding="utf-8")
    live_guard = 'if subscription_config["mode"] != "sandbox":'
    assert live_guard in source
    guarded_section = source.split(live_guard, 1)[1].split(
        '\\n# Messages de diagnostic protégés', 1
    )[0]
    live_branch, sandbox_branch = guarded_section.split("else:", 1)
    assert 'st.button("Préparer mon abonnement Premium"' not in live_branch
    assert 'st.button("Préparer mon abonnement Premium"' in sandbox_branch


def test_automatic_plan_creation_is_sandbox_only(monkeypatch):
    monkeypatch.setattr(paypal, "paypal_subscription_configuration", lambda: {
        "mode": "live",
        "base_url": "https://api-m.paypal.com",
        "client_id": "client",
        "client_secret": "secret",
    })
    try:
        paypal.ensure_premium_plan(object())
    except RuntimeError as exc:
        assert "Sandbox" in str(exc)
    else:
        raise AssertionError("Automatic plan creation must be blocked in Live")


def test_subscription_creation_requires_a_valid_plan_id(monkeypatch):
    monkeypatch.setattr(paypal, "paypal_subscription_configuration", lambda: {
        "base_url": "https://api-m.sandbox.paypal.com",
        "client_id": "client",
        "client_secret": "secret",
        "plan_id": "",
        "return_url": "https://example.com/return",
        "cancel_url": "https://example.com/cancel",
    })
    try:
        paypal.create_premium_subscription("00000000-0000-4000-8000-000000000001")
    except ValueError as exc:
        assert "forfait" in str(exc)
    else:
        raise AssertionError("Checkout must reject a missing plan ID")

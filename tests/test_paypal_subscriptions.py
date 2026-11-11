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

@pytest.mark.parametrize("url,expected", [
    ("https://api-m.sandbox.paypal.com/v1/next?page=2", True),
    ("http://api-m.sandbox.paypal.com/v1/next", False),
    ("https://api-m.sandbox.paypal.com.evil.test/v1/next", False),
    ("https://api-m.sandbox.paypal.com:8443/v1/next", False),
    ("https://attacker@api-m.sandbox.paypal.com/v1/next", False),
    ("https://api-m.sandbox.paypal.com/v1/next#fragment", False),
])
def test_paypal_pagination_url_requires_exact_https_authority(url, expected):
    assert paypal._is_trusted_paypal_pagination_url(
        url, "https://api-m.sandbox.paypal.com"
    ) is expected



def test_browser_return_never_persists_or_grants_active_subscription(monkeypatch):
    """Only the signed webhook may activate a recurring Premium entitlement."""
    from types import SimpleNamespace
    import premium_access

    class CatalogQuery:
        def select(self, *_args, **_kwargs):
            return self

        def eq(self, *_args, **_kwargs):
            return self

        def maybe_single(self):
            return self

        def execute(self):
            return SimpleNamespace(data={"paypal_plan_id": "P-PLAN123"})

    class ReadOnlyAdminClient:
        def table(self, name):
            assert name == "sowia_paypal_catalog"
            return CatalogQuery()

    monkeypatch.setattr(paypal, "paypal_subscription_configuration", lambda: {
        "mode": "sandbox",
        "base_url": "https://api-m.sandbox.paypal.com",
    })
    monkeypatch.setattr(premium_access, "create_admin_client", lambda: ReadOnlyAdminClient())
    monkeypatch.setattr(paypal, "get_premium_subscription", lambda _subscription_id: {
        "id": "I-ABC12345",
        "custom_id": "user-123",
        "plan_id": "P-PLAN123",
        "status": "ACTIVE",
        "billing_info": {"failed_payments_count": 0},
    })
    monkeypatch.setattr(paypal, "_access_token", lambda _config: "token")
    monkeypatch.setattr(paypal, "_validate_paypal_plan_price", lambda *_args: {"id": "P-PLAN123"})

    result = paypal.reconcile_returned_subscription("I-ABC12345", "user-123")

    assert result["status"] == "pending_webhook"
    assert result["paypal_subscription_id"] == "I-ABC12345"


def test_app_never_marks_browser_subscription_return_as_confirmed():
    from pathlib import Path

    source = Path("app.py").read_text(encoding="utf-8")
    assert 'st.session_state["paypal_subscription_returned"] = "pending_webhook"' in source
    assert 'st.session_state["paypal_subscription_returned"] = "confirmed"' not in source
    assert "Le retour navigateur ne donne aucun accès Premium." in source

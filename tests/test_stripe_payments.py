"""Tests for secure Stripe card checkout and Premium entitlement validation."""
from types import SimpleNamespace
import stripe_payments as payments


def test_stripe_checkout_is_disabled_by_default(monkeypatch):
    monkeypatch.setattr(payments, "_setting", lambda name, default="": default)
    assert payments.stripe_configuration() is None


def test_stripe_configuration_requires_complete_https_settings(monkeypatch):
    values = {
        "SOWIA_STRIPE_ENABLED": "true",
        "STRIPE_SECRET_KEY": "sk_test_example",
        "STRIPE_PREMIUM_PRICE_ID": "price_example",
        "STRIPE_SUCCESS_URL": "https://example.com/abonnement",
        "STRIPE_CANCEL_URL": "https://example.com/abonnement?stripe=cancel",
        "STRIPE_PREMIUM_PRICE_EUR": "9.90",
    }
    monkeypatch.setattr(payments, "_setting", lambda name, default="": values.get(name, default))
    config = payments.stripe_configuration()
    assert config["amount"] == "9.90"
    assert config["currency"] == "EUR"


def test_stripe_configuration_rejects_http_return_url(monkeypatch):
    values = {
        "SOWIA_STRIPE_ENABLED": "true", "STRIPE_SECRET_KEY": "sk_test_example",
        "STRIPE_PREMIUM_PRICE_ID": "price_example",
        "STRIPE_SUCCESS_URL": "http://example.com/success",
        "STRIPE_CANCEL_URL": "https://example.com/cancel",
    }
    monkeypatch.setattr(payments, "_setting", lambda name, default="": values.get(name, default))
    try:
        payments.stripe_configuration()
    except ValueError as exc:
        assert "HTTPS" in str(exc)
    else:
        raise AssertionError("HTTP success URL must be rejected")


def test_checkout_binds_authenticated_user_and_uses_hosted_card_checkout(monkeypatch):
    monkeypatch.setattr(payments, "stripe_configuration", lambda: {
        "secret_key": "sk_test", "price_id": "price_test",
        "success_url": "https://example.com/success",
        "cancel_url": "https://example.com/cancel",
        "amount": "9.90", "currency": "EUR",
    })
    calls = {}
    class Session:
        @staticmethod
        def create(**kwargs):
            calls.update(kwargs)
            return {"id": "cs_test_123", "url": "https://checkout.stripe.com/pay/test"}
    import stripe
    monkeypatch.setattr(stripe, "checkout", SimpleNamespace(Session=Session))
    result = payments.create_card_checkout("user-123")
    assert result["id"] == "cs_test_123"
    assert calls["payment_method_types"] == ["card"]
    assert calls["client_reference_id"] == "user-123"
    assert calls["metadata"]["sowia_user_id"] == "user-123"
    assert calls["line_items"][0]["price"] == "price_test"


def test_retrieve_checkout_requires_paid_matching_session(monkeypatch):
    monkeypatch.setattr(payments, "stripe_configuration", lambda: {
        "secret_key": "sk_test", "price_id": "price_test",
        "success_url": "https://example.com/success",
        "cancel_url": "https://example.com/cancel",
        "amount": "9.90", "currency": "EUR",
    })
    class Session:
        @staticmethod
        def retrieve(session_id, **kwargs):
            return {
                "id": session_id, "mode": "payment", "payment_status": "paid",
                "client_reference_id": "user-123",
                "metadata": {"sowia_user_id": "user-123", "sowia_product": "premium"},
                "currency": "eur", "amount_total": 990,
                "payment_intent": "pi_test_123",
                "line_items": {"data": [{"price": {"id": "price_test"}, "quantity": 1}]},
            }
    import stripe
    monkeypatch.setattr(stripe, "checkout", SimpleNamespace(Session=Session))
    monkeypatch.setattr(stripe, "PaymentIntent", SimpleNamespace(retrieve=lambda *args, **kwargs: {
        "status": "succeeded", "amount_received": 990, "currency": "eur",
        "latest_charge": {"id": "ch_test_123", "amount_captured": 990, "amount_refunded": 0, "disputed": False},
    }))
    result = payments.retrieve_paid_checkout("cs_test_123", "user-123")
    assert result["payment_intent_id"] == "pi_test_123"
    assert result["amount"] == "9.90"


def test_retrieve_checkout_rejects_unpaid_or_wrong_owner(monkeypatch):
    monkeypatch.setattr(payments, "stripe_configuration", lambda: {
        "secret_key": "sk_test", "price_id": "price_test",
        "success_url": "https://example.com/success",
        "cancel_url": "https://example.com/cancel",
        "amount": "9.90", "currency": "EUR",
    })
    class Session:
        @staticmethod
        def retrieve(session_id, **kwargs):
            return {
                "id": session_id, "mode": "payment", "payment_status": "unpaid",
                "client_reference_id": "other-user",
                "metadata": {"sowia_user_id": "other-user", "sowia_product": "premium"},
                "currency": "eur", "amount_total": 990, "payment_intent": "pi_test_123",
                "line_items": {"data": [{"price": {"id": "price_test"}, "quantity": 1}]},
            }
    import stripe
    monkeypatch.setattr(stripe, "checkout", SimpleNamespace(Session=Session))
    try:
        payments.retrieve_paid_checkout("cs_test_123", "user-123")
    except PermissionError:
        pass
    else:
        raise AssertionError("Unpaid checkout must never grant Premium")

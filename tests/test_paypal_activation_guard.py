"""Payment activation must remain explicitly opt-in."""

import paypal_payments


def test_payments_are_disabled_by_default(monkeypatch):
    monkeypatch.setattr(paypal_payments, "_setting", lambda name, default="": default)
    assert paypal_payments.paypal_configuration() is None


def test_payments_require_explicit_owner_enablement(monkeypatch):
    settings = {
        "SOWIA_PAYMENTS_ENABLED": "true",
        "PAYPAL_CLIENT_ID": "test-client",
        "PAYPAL_CLIENT_SECRET": "test-secret",
        "PAYPAL_PREMIUM_PRICE": "9.99",
        "PAYPAL_CURRENCY": "EUR",
        "PAYPAL_MODE": "sandbox",
        "PAYPAL_RETURN_URL": "https://example.test/return",
        "PAYPAL_CANCEL_URL": "https://example.test/cancel",
    }
    monkeypatch.setattr(paypal_payments, "_setting", lambda name, default="": settings.get(name, default))
    config = paypal_payments.paypal_configuration()
    assert config is not None
    assert config["mode"] == "sandbox"
    assert config["amount"] == "9.99"

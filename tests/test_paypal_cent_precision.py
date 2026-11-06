"""Regression tests for exact PayPal cent precision."""
import pytest

import paypal_payments as paypal


@pytest.mark.parametrize("price", ["12.999", "12.901", "0.001", "NaN", "Infinity"])
def test_paypal_configuration_rejects_non_cent_or_non_finite_prices(monkeypatch, price):
    values = {
        "SOWIA_PAYMENTS_ENABLED": "true",
        "PAYPAL_CLIENT_ID": "sandbox-client",
        "PAYPAL_CLIENT_SECRET": "sandbox-secret",
        "PAYPAL_PREMIUM_PRICE": price,
        "PAYPAL_CURRENCY": "EUR",
        "PAYPAL_MODE": "sandbox",
        "PAYPAL_RETURN_URL": "https://example.test/return",
        "PAYPAL_CANCEL_URL": "https://example.test/cancel",
    }
    monkeypatch.setattr(
        paypal,
        "get_setting",
        lambda key, default="": values.get(key, default),
    )
    with pytest.raises(ValueError, match="montant exact|montant en euros valide"):
        paypal.paypal_configuration()


@pytest.mark.parametrize(
    "price, expected",
    [("12.90", "12.90"), ("12.9", "12.90"), ("0.01", "0.01")],
)
def test_paypal_configuration_accepts_exact_cent_amounts(monkeypatch, price, expected):
    values = {
        "SOWIA_PAYMENTS_ENABLED": "true",
        "PAYPAL_CLIENT_ID": "sandbox-client",
        "PAYPAL_CLIENT_SECRET": "sandbox-secret",
        "PAYPAL_PREMIUM_PRICE": price,
        "PAYPAL_CURRENCY": "EUR",
        "PAYPAL_MODE": "sandbox",
        "PAYPAL_RETURN_URL": "https://example.test/return",
        "PAYPAL_CANCEL_URL": "https://example.test/cancel",
    }
    monkeypatch.setattr(
        paypal,
        "get_setting",
        lambda key, default="": values.get(key, default),
    )
    assert paypal.paypal_configuration()["amount"] == expected

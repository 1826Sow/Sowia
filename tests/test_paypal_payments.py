import pytest

import paypal_payments as paypal


def _settings(monkeypatch, **overrides):
    values = {
        "PAYPAL_ENABLED": "true",
        "PAYPAL_CLIENT_ID": "sandbox-client",
        "PAYPAL_CLIENT_SECRET": "sandbox-secret",
        "PAYPAL_PREMIUM_PRICE": "12.90",
        "PAYPAL_CURRENCY": "EUR",
        "PAYPAL_MODE": "sandbox",
        "PAYPAL_RETURN_URL": "https://example.test/return",
        "PAYPAL_CANCEL_URL": "https://example.test/cancel",
    }
    values.update(overrides)
    monkeypatch.setattr(paypal, "get_setting", lambda key, default="": values.get(key, default))


def test_configuration_is_disabled_until_all_secrets_exist(monkeypatch):
    _settings(monkeypatch, PAYPAL_CLIENT_SECRET="")
    assert paypal.paypal_configuration() is None


def test_configuration_uses_sandbox_and_euro_amount(monkeypatch):
    _settings(monkeypatch, PAYPAL_PREMIUM_PRICE="12.9")
    config = paypal.paypal_configuration()
    assert config["base_url"] == "https://api-m.sandbox.paypal.com"
    assert config["amount"] == "12.90"
    assert config["currency"] == "EUR"


def test_configuration_rejects_non_https_return_url(monkeypatch):
    _settings(monkeypatch, PAYPAL_RETURN_URL="http://example.test/return")
    with pytest.raises(ValueError, match="HTTPS"):
        paypal.paypal_configuration()


def test_capture_refuses_order_belonging_to_another_user(monkeypatch):
    _settings(monkeypatch)
    class Response:
        def __init__(self, data):
            self.data = data
        def raise_for_status(self):
            pass
        def json(self):
            return self.data

    calls = []
    def fake_post(url, **kwargs):
        calls.append(("post", url))
        return Response({"access_token": "test-token"})
    def fake_get(url, **kwargs):
        calls.append(("get", url))
        return Response({
            "id": "ORDER-1",
            "intent": "CAPTURE",
            "status": "APPROVED",
            "purchase_units": [{
                "custom_id": "different-user",
                "reference_id": "sowia-premium",
                "amount": {"currency_code": "EUR", "value": "12.90"},
            }],
        })

    monkeypatch.setattr(paypal.requests, "post", fake_post)
    monkeypatch.setattr(paypal.requests, "get", fake_get)
    with pytest.raises(PermissionError, match="ne correspond pas"):
        paypal.capture_premium_order("ORDER-1", "current-user")
    assert [kind for kind, _ in calls] == ["post", "get"]


def test_paypal_remains_disabled_even_when_credentials_are_present(monkeypatch):
    _settings(monkeypatch, PAYPAL_ENABLED="false")
    assert paypal.paypal_configuration() is None

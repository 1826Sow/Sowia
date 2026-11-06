import pytest

import paypal_payments as paypal


def _settings(monkeypatch, **overrides):
    values = {
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


def _completed_order(order_id="ORDER-1", user_id="current-user", amount="12.90", currency="EUR", status="COMPLETED"):
    return {
        "id": order_id,
        "status": "COMPLETED",
        "purchase_units": [{
            "custom_id": user_id,
            "reference_id": "sowia-premium",
            "payments": {
                "captures": [{
                    "status": status,
                    "amount": {"currency_code": currency, "value": amount},
                }]
            },
        }],
    }


def test_completed_payment_requires_matching_capture():
    config = {"amount": "12.90", "currency": "EUR"}
    result = paypal._validate_completed_payment(
        _completed_order(), "ORDER-1", "current-user", config
    )
    assert result["status"] == "COMPLETED"


@pytest.mark.parametrize("order, message", [
    (_completed_order(amount="1.00"), "montant ou le statut"),
    (_completed_order(currency="USD"), "montant ou le statut"),
    (_completed_order(status="PENDING"), "montant ou le statut"),
    (_completed_order(user_id="another-user"), "ne correspond pas"),
    (_completed_order(order_id="OTHER-ORDER"), "commande"),
])
def test_completed_payment_rejects_invalid_capture(order, message):
    config = {"amount": "12.90", "currency": "EUR"}
    with pytest.raises((RuntimeError, PermissionError), match=message):
        paypal._validate_completed_payment(order, "ORDER-1", "current-user", config)


def test_completed_payment_requires_exactly_one_capture():
    order = _completed_order()
    order["purchase_units"][0]["payments"]["captures"].append(
        order["purchase_units"][0]["payments"]["captures"][0]
    )
    with pytest.raises(RuntimeError, match="capture de paiement unique"):
        paypal._validate_completed_payment(
            order, "ORDER-1", "current-user",
            {"amount": "12.90", "currency": "EUR"},
        )

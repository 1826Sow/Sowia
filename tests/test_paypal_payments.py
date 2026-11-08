import pytest

import paypal_payments as paypal


def _settings(monkeypatch, **overrides):
    values = {
        "SOWIA_PAYMENTS_ENABLED": "true",
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
            "id": "ORDER1",
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
        paypal.capture_premium_order("ORDER1", "current-user")
    assert [kind for kind, _ in calls] == ["post", "get"]


def test_payments_remain_disabled_without_explicit_enable_flag(monkeypatch):
    _settings(monkeypatch, SOWIA_PAYMENTS_ENABLED="false")
    assert paypal.paypal_configuration() is None


@pytest.mark.parametrize(
    "details, expected_message",
    [
        (
            {
                "id": "ORDER1",
                "intent": "CAPTURE",
                "status": "APPROVED",
                "purchase_units": [{
                    "custom_id": "current-user",
                    "reference_id": "sowia-premium",
                    "amount": {"currency_code": "EUR", "value": "99.00"},
                }],
            },
            "ne correspond pas",
        ),
        (
            {
                "id": "ORDER1",
                "intent": "CAPTURE",
                "status": "APPROVED",
                "purchase_units": [{
                    "custom_id": "current-user",
                    "reference_id": "sowia-premium",
                    "amount": {"currency_code": "USD", "value": "12.90"},
                }],
            },
            "ne correspond pas",
        ),
        (
            {
                "id": "ORDER1",
                "intent": "AUTHORIZE",
                "status": "APPROVED",
                "purchase_units": [{
                    "custom_id": "current-user",
                    "reference_id": "sowia-premium",
                    "amount": {"currency_code": "EUR", "value": "12.90"},
                }],
            },
            "ne correspond pas",
        ),
        (
            {
                "id": "ORDER1",
                "intent": "CAPTURE",
                "status": "CREATED",
                "purchase_units": [{
                    "custom_id": "current-user",
                    "reference_id": "sowia-premium",
                    "amount": {"currency_code": "EUR", "value": "12.90"},
                }],
            },
            "ne correspond pas",
        ),
    ],
)
def test_capture_refuses_order_with_wrong_amount_currency_intent_or_status(
    monkeypatch, details, expected_message
):
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
        return Response(details)

    monkeypatch.setattr(paypal.requests, "post", fake_post)
    monkeypatch.setattr(paypal.requests, "get", fake_get)

    with pytest.raises(PermissionError, match=expected_message):
        paypal.capture_premium_order("ORDER1", "current-user")

    # Only the OAuth token request is allowed; no capture request is sent.
    assert [kind for kind, _ in calls] == ["post", "get"]


def test_completed_order_is_not_captured_twice(monkeypatch):
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
            "id": "ORDER1",
            "intent": "CAPTURE",
            "status": "COMPLETED",
            "purchase_units": [{
                "custom_id": "current-user",
                "reference_id": "sowia-premium",
                "amount": {"currency_code": "EUR", "value": "12.90"},
            }],
        })

    monkeypatch.setattr(paypal.requests, "post", fake_post)
    monkeypatch.setattr(paypal.requests, "get", fake_get)

    result = paypal.capture_premium_order("ORDER1", "current-user")

    assert result["status"] == "COMPLETED"
    # Token request + order lookup only; no duplicate capture POST.
    assert [kind for kind, _ in calls] == ["post", "get"]

@pytest.mark.parametrize("order_id", ["../capture", "ORDER/1", "order-1", "ORDER 1", "?token=x", "A" * 51])
def test_capture_rejects_malformed_order_id_before_network_calls(monkeypatch, order_id):
    _settings(monkeypatch)
    calls = []
    monkeypatch.setattr(
        paypal,
        "_access_token",
        lambda config: calls.append("token") or "test-token",
    )
    with pytest.raises(PermissionError, match="Identifiant de commande"):
        paypal.capture_premium_order(order_id, "current-user")
    assert calls == []


def test_capture_rejects_response_with_different_order_id(monkeypatch):
    _settings(monkeypatch)

    class Response:
        def __init__(self, data):
            self.data = data

        def raise_for_status(self):
            pass

        def json(self):
            return self.data

    calls = []
    monkeypatch.setattr(paypal, "_access_token", lambda config: "test-token")

    def fake_get(url, **kwargs):
        calls.append(url)
        return Response({"id": "OTHERORDER", "purchase_units": []})

    monkeypatch.setattr(paypal.requests, "get", fake_get)
    with pytest.raises(PermissionError, match="ne correspond pas"):
        paypal.capture_premium_order("ORDER123", "current-user")
    assert len(calls) == 1

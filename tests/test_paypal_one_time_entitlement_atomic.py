import pytest

from financial_ledger import grant_paypal_one_time_entitlement


class RpcQuery:
    def __init__(self, client, name, params):
        self.client = client
        self.name = name
        self.params = params

    def execute(self):
        return type("Result", (), {"data": self.client.outcome})()


class Client:
    def __init__(self, outcome="granted"):
        self.outcome = outcome
        self.calls = []

    def rpc(self, name, params):
        self.calls.append((name, params))
        return RpcQuery(self, name, params)


def test_one_time_paypal_grant_uses_single_atomic_rpc():
    client = Client("granted")
    result = grant_paypal_one_time_entitlement(
        client,
        user_id="user-123",
        order_id="ORDER123",
        capture={"id": "CAPTURE123"},
        amount="12.90",
        currency="EUR",
    )
    assert result == "granted"
    assert len(client.calls) == 1
    name, params = client.calls[0]
    assert name == "sowia_grant_paypal_one_time_entitlement"
    assert params == {
        "p_user_id": "user-123",
        "p_order_id": "ORDER123",
        "p_capture_id": "CAPTURE123",
        "p_amount": "12.90",
        "p_currency": "EUR",
    }


@pytest.mark.parametrize("outcome", ["already_granted", "replay_ignored"])
def test_one_time_paypal_grant_accepts_safe_idempotent_outcomes(outcome):
    client = Client(outcome)
    assert grant_paypal_one_time_entitlement(
        client,
        user_id="user-123",
        order_id="ORDER123",
        capture={"id": "CAPTURE123"},
        amount="12.90",
        currency="EUR",
    ) == outcome


@pytest.mark.parametrize(
    "kwargs",
    [
        {"user_id": "", "order_id": "ORDER123", "capture": {"id": "CAPTURE123"}, "amount": "12.90", "currency": "EUR"},
        {"user_id": "user-123", "order_id": "../", "capture": {"id": "CAPTURE123"}, "amount": "12.90", "currency": "EUR"},
        {"user_id": "user-123", "order_id": "ORDER123", "capture": {"id": "bad/id"}, "amount": "12.90", "currency": "EUR"},
        {"user_id": "user-123", "order_id": "ORDER123", "capture": {"id": "CAPTURE123"}, "amount": "0", "currency": "EUR"},
        {"user_id": "user-123", "order_id": "ORDER123", "capture": {"id": "CAPTURE123"}, "amount": "12.901", "currency": "EUR"},
        {"user_id": "user-123", "order_id": "ORDER123", "capture": {"id": "CAPTURE123"}, "amount": "12.90", "currency": "USD"},
    ],
)
def test_invalid_one_time_payment_is_rejected_before_rpc(kwargs):
    client = Client()
    with pytest.raises(ValueError):
        grant_paypal_one_time_entitlement(client, **kwargs)
    assert client.calls == []


def test_requires_admin_client_for_atomic_grant():
    with pytest.raises(RuntimeError):
        grant_paypal_one_time_entitlement(
            None,
            user_id="user-123",
            order_id="ORDER123",
            capture={"id": "CAPTURE123"},
            amount="12.90",
            currency="EUR",
        )


def test_unexpected_rpc_response_fails_closed():
    client = Client("unknown")
    with pytest.raises(RuntimeError, match="résultat inattendu"):
        grant_paypal_one_time_entitlement(
            client,
            user_id="user-123",
            order_id="ORDER123",
            capture={"id": "CAPTURE123"},
            amount="12.90",
            currency="EUR",
        )

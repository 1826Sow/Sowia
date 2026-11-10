import pytest

from financial_ledger import record_paypal_capture


class Query:
    def __init__(self, client):
        self.client = client
    def upsert(self, payload, **kwargs):
        self.client.payload = payload
        self.client.kwargs = kwargs
        return self
    def execute(self):
        return type("Result", (), {"data": [self.client.payload]})()


class Client:
    def table(self, name):
        assert name == "sowia_financial_transactions"
        return Query(self)


def test_records_confirmed_paypal_capture_idempotently():
    client = Client()
    result = record_paypal_capture(
        client, user_id="u1", order_id="ORDER123",
        capture={"id": "CAPTURE123"}, amount="12.90", currency="EUR",
    )
    assert result[0]["provider"] == "paypal"
    assert result[0]["provider_payment_id"] == "CAPTURE123"
    assert result[0]["status"] == "confirmed"
    assert client.kwargs["on_conflict"] == "provider,provider_payment_id,transaction_type"
    assert client.kwargs["ignore_duplicates"] is True


@pytest.mark.parametrize("kwargs", [
    {"user_id": "", "order_id": "ORDER123", "capture": {"id": "CAPTURE123"}, "amount": "12", "currency": "EUR"},
    {"user_id": "u1", "order_id": "../", "capture": {"id": "CAPTURE123"}, "amount": "12", "currency": "EUR"},
    {"user_id": "u1", "order_id": "ORDER123", "capture": {"id": "x"}, "amount": "12", "currency": "EUR"},
    {"user_id": "u1", "order_id": "ORDER123", "capture": {"id": "CAPTURE123"}, "amount": "0", "currency": "EUR"},
    {"user_id": "u1", "order_id": "ORDER123", "capture": {"id": "CAPTURE123"}, "amount": "12", "currency": "USD"},
])
def test_rejects_invalid_paypal_capture(kwargs):
    with pytest.raises(ValueError):
        record_paypal_capture(Client(), **kwargs)


def test_requires_admin_client():
    with pytest.raises(RuntimeError):
        record_paypal_capture(None, user_id="u1", order_id="ORDER123",
                              capture={"id": "CAPTURE123"}, amount="12", currency="EUR")

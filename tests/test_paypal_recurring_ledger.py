import pytest

from financial_ledger import record_paypal_billing_transaction


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


def _transaction(**overrides):
    value = {
        "id": "BILLINGTX123",
        "status": "COMPLETED",
        "time": "2026-11-10T12:00:00Z",
        "amount_with_breakdown": {
            "gross_amount": {"currency_code": "EUR", "value": "9.90"},
            "fee_amount": {"currency_code": "EUR", "value": "0.49"},
            "net_amount": {"currency_code": "EUR", "value": "9.41"},
        },
    }
    value.update(overrides)
    return value


def test_records_completed_recurring_payment_and_actual_fee_net():
    client = Client()
    result = record_paypal_billing_transaction(
        client, user_id="u1", subscription_id="I-ABC123", transaction=_transaction()
    )
    row = result[0]
    assert row["provider_payment_id"] == "BILLINGTX123"
    assert row["gross_amount"] == "9.90"
    assert row["fee_amount"] == "0.49"
    assert row["net_amount"] == "9.41"
    assert client.kwargs["ignore_duplicates"] is True


@pytest.mark.parametrize("status", ["PENDING", "DENIED", "REFUNDED", ""])
def test_rejects_non_completed_recurring_transaction(status):
    with pytest.raises(ValueError, match="COMPLETED"):
        record_paypal_billing_transaction(
            Client(), user_id="u1", subscription_id="I-ABC123",
            transaction=_transaction(status=status)
        )


def test_rejects_wrong_currency_and_invalid_id():
    tx = _transaction()
    tx["amount_with_breakdown"]["gross_amount"]["currency_code"] = "USD"
    with pytest.raises(ValueError, match="EUR"):
        record_paypal_billing_transaction(
            Client(), user_id="u1", subscription_id="I-ABC123", transaction=tx
        )
    with pytest.raises(ValueError):
        record_paypal_billing_transaction(
            Client(), user_id="u1", subscription_id="../bad", transaction=_transaction()
        )


def test_unknown_fee_and_net_remain_null():
    tx = _transaction(amount_with_breakdown={
        "gross_amount": {"currency_code": "EUR", "value": "9.90"}
    })
    result = record_paypal_billing_transaction(
        Client(), user_id="u1", subscription_id="I-ABC123", transaction=tx
    )[0]
    assert result["fee_amount"] is None
    assert result["net_amount"] is None

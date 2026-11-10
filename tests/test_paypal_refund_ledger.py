from decimal import Decimal

import pytest

from financial_ledger import record_paypal_refund_total


class Query:
    def __init__(self, client):
        self.client = client
    def update(self, payload):
        self.client.updates.append(payload)
        return self
    def upsert(self, payload, **kwargs):
        self.client.payload = payload
        self.client.kwargs = kwargs
        return self
    def eq(self, *_):
        return self
    def execute(self):
        return type("Result", (), {"data": [self.client.payload] if self.client.payload else []})()


class Client:
    def __init__(self):
        self.payload = None
        self.kwargs = None
        self.updates = []
    def table(self, name):
        assert name == "sowia_financial_transactions"
        return Query(self)


def capture(status="PARTIALLY_REFUNDED", refunded="2.50"):
    return {
        "id": "CAPTURE123",
        "status": status,
        "amount": {"currency_code": "EUR", "value": "9.90"},
        "seller_receivable_breakdown": {
            "gross_amount": {"currency_code": "EUR", "value": "9.90"},
            "total_refunded_amount": {"currency_code": "EUR", "value": refunded},
        },
        "update_time": "2026-11-10T10:30:00Z",
    }


def test_records_cumulative_partial_refund_as_idempotent_aggregate():
    client = Client()
    record_paypal_refund_total(client, user_id="u1", capture=capture())
    assert client.updates == [{"status": "confirmed"}]
    assert client.payload["transaction_type"] == "refund"
    assert client.payload["provider_payment_id"] == "AGGREGATE-CAPTURE123"
    assert client.payload["gross_amount"] == "2.50"
    assert client.payload["status"] == "refunded"
    assert client.kwargs["on_conflict"] == "provider,provider_payment_id,transaction_type"
    assert "ignore_duplicates" not in client.kwargs


def test_cumulative_total_can_be_updated_without_double_counting():
    client = Client()
    record_paypal_refund_total(client, user_id="u1", capture=capture(refunded="4.00"))
    assert Decimal(client.payload["gross_amount"]) == Decimal("4.00")


@pytest.mark.parametrize("details", [
    capture(status="COMPLETED"),
    capture(refunded="0"),
    capture(refunded="10.00"),
    capture(status="REFUNDED", refunded="2.50"),
])
def test_rejects_inconsistent_refund_details(details):
    with pytest.raises(ValueError):
        record_paypal_refund_total(Client(), user_id="u1", capture=details)


def test_rejects_wrong_currency():
    details = capture()
    details["seller_receivable_breakdown"]["total_refunded_amount"]["currency_code"] = "USD"
    with pytest.raises(ValueError):
        record_paypal_refund_total(Client(), user_id="u1", capture=details)

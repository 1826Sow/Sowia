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

def test_refunded_capture_is_flagged_not_counted_as_income():
    from financial_ledger import flag_paypal_refund_for_review

    class UpdateQuery:
        def __init__(self):
            self.filters = []
        def update(self, payload):
            self.payload = payload
            return self
        def eq(self, key, value):
            self.filters.append((key, value))
            return self
        def execute(self):
            return type("Result", (), {"data": [{"status": self.payload["status"]}]})()

    class ReviewClient:
        def table(self, name):
            assert name == "sowia_financial_transactions"
            return UpdateQuery()

    result = flag_paypal_refund_for_review(
        ReviewClient(), user_id="u1",
        transaction={
            "id": "CAPTURE123", "status": "PARTIALLY_REFUNDED",
            "time": "2026-11-10T10:00:00Z",
            "amount_with_breakdown": {
                "gross_amount": {"currency_code": "EUR", "value": "9.90"}
            },
        },
    )
    assert result["status"] == "manual_review"
    assert result["updated"] is True


def test_refund_review_rejects_untrusted_status_and_currency():
    from financial_ledger import flag_paypal_refund_for_review

    class UnusedClient:
        def table(self, _):
            raise AssertionError("Must validate before database access")

    base = {
        "id": "CAPTURE123", "status": "COMPLETED",
        "time": "2026-11-10T10:00:00Z",
        "amount_with_breakdown": {
            "gross_amount": {"currency_code": "EUR", "value": "9.90"}
        },
    }
    with pytest.raises(ValueError):
        flag_paypal_refund_for_review(UnusedClient(), user_id="u1", transaction=base)
    base["status"] = "REFUNDED"
    base["amount_with_breakdown"]["gross_amount"]["currency_code"] = "USD"
    with pytest.raises(ValueError):
        flag_paypal_refund_for_review(UnusedClient(), user_id="u1", transaction=base)


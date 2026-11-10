import pytest

from financial_ledger import record_paypal_refund_for_review


class Result:
    def __init__(self, data):
        self.data = data


class Query:
    def __init__(self, client):
        self.client = client
        self.filters = []
        self.payload = None
        self.operation = "select"

    def select(self, *_args):
        query = Query(self.client)
        query.operation = "select"
        return query

    def eq(self, key, value):
        self.filters.append((key, value))
        return self

    def limit(self, *_args):
        return self

    def update(self, payload):
        query = Query(self.client)
        query.operation = "update"
        query.payload = payload
        return query

    def upsert(self, payload, **_kwargs):
        query = Query(self.client)
        query.operation = "upsert"
        query.payload = payload
        return query

    def execute(self):
        rows = list(self.client.rows)
        for key, value in self.filters:
            rows = [row for row in rows if row.get(key) == value]
        if self.operation == "upsert":
            self.client.writes.append(self.payload)
            return Result([self.payload])
        if self.operation == "update":
            self.client.updates.append((self.filters, self.payload))
            return Result([])
        return Result(rows)


class Admin:
    def __init__(self, rows):
        self.rows = rows
        self.writes = []
        self.updates = []

    def table(self, _name):
        return Query(self)


def base_refund(refund_id, amount):
    return {
        "id": refund_id,
        "amount": {"currency": "EUR", "value": amount},
        "create_time": "2026-11-02T10:00:00Z",
    }


def capture():
    return {"provider_payment_id": "CAPTURE12345", "gross_amount": "10.00"}


def test_partial_refunds_cannot_exceed_capture_total():
    admin = Admin([
        {"user_id": "u1", "provider": "paypal", "provider_payment_id": "CAPTURE12345",
         "transaction_type": "payment", "gross_amount": "10.00"},
        {"user_id": "u1", "provider": "paypal", "provider_payment_id": "REFUND00001",
         "parent_capture_id": "CAPTURE12345", "transaction_type": "refund", "gross_amount": "7.00"},
    ])
    with pytest.raises(ValueError, match="cumul"):
        record_paypal_refund_for_review(
            admin, user_id="u1", capture_row=capture(),
            refund=base_refund("REFUND00002", "3.01"),
        )
    assert admin.writes == []


def test_refund_retry_does_not_double_count_same_refund_id():
    admin = Admin([
        {"user_id": "u1", "provider": "paypal", "provider_payment_id": "CAPTURE12345",
         "transaction_type": "payment", "gross_amount": "10.00"},
        {"user_id": "u1", "provider": "paypal", "provider_payment_id": "REFUND00001",
         "parent_capture_id": "CAPTURE12345", "transaction_type": "refund", "gross_amount": "7.00"},
    ])
    result = record_paypal_refund_for_review(
        admin, user_id="u1", capture_row=capture(),
        refund=base_refund("REFUND00001", "7.00"),
    )
    assert result["status"] == "manual_review"
    assert admin.writes[0]["parent_capture_id"] == "CAPTURE12345"


def test_refund_requires_capture_owned_by_same_user():
    admin = Admin([])
    with pytest.raises(PermissionError):
        record_paypal_refund_for_review(
            admin, user_id="other-user", capture_row=capture(),
            refund=base_refund("REFUND00001", "1.00"),
        )

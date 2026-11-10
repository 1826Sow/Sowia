"""Regression tests for PayPal recurring billing rows in the financial ledger."""
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
    transaction = {
        "id": "BILLING123",
        "status": "COMPLETED",
        "time": "2026-11-10T10:00:00Z",
        "amount_with_breakdown": {
            "gross_amount": {"currency_code": "EUR", "value": "9.90"},
            "fee_amount": {"currency_code": "EUR", "value": "0.59"},
            "net_amount": {"currency_code": "EUR", "value": "9.31"},
        },
    }
    transaction.update(overrides)
    return transaction


def test_records_completed_recurring_billing_idempotently():
    client = Client()
    result = record_paypal_billing_transaction(
        client,
        user_id="user-1",
        subscription_id="I-TEST12345",
        transaction=_transaction(),
    )

    row = result[0]
    assert row["provider"] == "paypal"
    assert row["provider_payment_id"] == "BILLING123"
    assert row["transaction_type"] == "payment"
    assert row["status"] == "confirmed"
    assert row["gross_amount"] == "9.90"
    assert row["gross_currency"] == "EUR"
    assert row["fee_amount"] == "0.59"
    assert row["net_amount"] == "9.31"
    assert row["occurred_at"] == "2026-11-10T10:00:00Z"
    assert client.kwargs["on_conflict"] == "provider,provider_payment_id,transaction_type"
    assert client.kwargs["ignore_duplicates"] is True


@pytest.mark.parametrize("status", ["PENDING", "DENIED", "REFUNDED", ""])
def test_non_completed_recurring_transaction_is_never_recorded(status):
    client = Client()
    with pytest.raises(ValueError, match="COMPLETED"):
        record_paypal_billing_transaction(
            client,
            user_id="user-1",
            subscription_id="I-TEST12345",
            transaction=_transaction(status=status),
        )


@pytest.mark.parametrize(
    "user_id,subscription_id,transaction",
    [
        ("", "I-TEST12345", _transaction()),
        ("user-1", "not-a-subscription", _transaction()),
        ("user-1", "I-TEST12345", {"id": "../bad", "status": "COMPLETED"}),
        ("user-1", "I-TEST12345", _transaction(
            amount_with_breakdown={"gross_amount": {"currency_code": "USD", "value": "9.90"}}
        )),
        ("user-1", "I-TEST12345", _transaction(time="")),
    ],
)
def test_rejects_invalid_recurring_billing_data_before_database_write(
    user_id, subscription_id, transaction
):
    class UnusedClient:
        def table(self, _):
            raise AssertionError("Invalid data must be rejected before database access")

    with pytest.raises(ValueError):
        record_paypal_billing_transaction(
            UnusedClient(),
            user_id=user_id,
            subscription_id=subscription_id,
            transaction=transaction,
        )


def test_recurring_billing_keeps_missing_fee_and_net_unknown():
    client = Client()
    transaction = _transaction(
        amount_with_breakdown={
            "gross_amount": {"currency_code": "EUR", "value": "9.90"}
        }
    )
    row = record_paypal_billing_transaction(
        client,
        user_id="user-1",
        subscription_id="I-TEST12345",
        transaction=transaction,
    )[0]

    assert row["fee_amount"] is None
    assert row["fee_currency"] is None
    assert row["net_amount"] is None
    assert row["net_currency"] is None


def test_requires_admin_client_for_recurring_billing():
    with pytest.raises(RuntimeError):
        record_paypal_billing_transaction(
            None,
            user_id="user-1",
            subscription_id="I-TEST12345",
            transaction=_transaction(),
        )

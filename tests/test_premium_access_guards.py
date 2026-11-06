"""Negative tests for Premium entitlement access and grant validation."""
from types import SimpleNamespace

import pytest

import premium_access


class Query:
    def __init__(self, data):
        self.data = data
        self.filters = []

    def select(self, fields):
        return self

    def eq(self, field, value):
        self.filters.append((field, value))
        return self

    def maybe_single(self):
        return self

    def execute(self):
        return SimpleNamespace(data=self.data)


class Client:
    def __init__(self, data):
        self.query = Query(data)

    def table(self, name):
        assert name == "sowia_entitlements"
        return self.query


class User:
    id = "user-123"


@pytest.mark.parametrize(
    "data",
    [
        None,
        {"status": "inactive"},
        {"status": "cancelled"},
        {"status": "pending"},
    ],
)
def test_only_active_entitlement_is_returned(data):
    assert premium_access.get_entitlement(Client(data), User()) is None


@pytest.mark.parametrize(
    "arguments",
    [
        ("", "ORDER-1", "12.90", "EUR"),
        ("user-123", "", "12.90", "EUR"),
        ("user-123", "ORDER-1", "", "EUR"),
        ("user-123", "ORDER-1", "12.90", "USD"),
        ("user-123", "ORDER-1", "0", "EUR"),
        ("user-123", "ORDER-1", "-1.00", "EUR"),
        ("user-123", "ORDER-1", "not-a-price", "EUR"),
        ("user-123", "ORDER-1", "10000", "EUR"),
    ],
)
def test_entitlement_grant_rejects_incomplete_or_invalid_payment(arguments):
    client = Client(None)
    with pytest.raises(ValueError):
        premium_access.grant_paypal_entitlement(client, *arguments)


def test_entitlement_lookup_requires_authenticated_user():
    with pytest.raises(PermissionError, match="Connexion requise"):
        premium_access.get_entitlement(Client(None), None)


def test_grant_normalizes_amount_and_uses_user_scoped_upsert():
    class WriteQuery:
        def __init__(self):
            self.payload = None
            self.conflict = None

        def upsert(self, payload, on_conflict):
            self.payload = payload
            self.conflict = on_conflict
            return self

        def execute(self):
            return SimpleNamespace(data=[self.payload])

    class WriteClient:
        def __init__(self):
            self.query = WriteQuery()

        def table(self, name):
            assert name == "sowia_entitlements"
            return self.query

    client = WriteClient()
    premium_access.grant_paypal_entitlement(client, " user-123 ", " ORDER-1 ", "12.9", "EUR")
    assert client.query.payload["user_id"] == "user-123"
    assert client.query.payload["paypal_order_id"] == "ORDER-1"
    assert client.query.payload["amount"] == "12.90"
    assert client.query["currency"] if False else client.query.conflict == "user_id"

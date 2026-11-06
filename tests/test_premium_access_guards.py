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
    ],
)
def test_entitlement_grant_rejects_incomplete_or_wrong_currency(arguments):
    client = Client(None)
    with pytest.raises(ValueError):
        premium_access.grant_paypal_entitlement(client, *arguments)

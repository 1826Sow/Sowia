from types import SimpleNamespace

import pytest
import premium_access


class User:
    id = "user-123"


class Query:
    def __init__(self, data=None):
        self.data = data
        self.filters = []
        self.payload = None
    def select(self, fields):
        self.fields = fields
        return self
    def eq(self, field, value):
        self.filters.append((field, value))
        return self
    def maybe_single(self):
        return self
    def upsert(self, payload, on_conflict=None):
        self.payload = payload
        self.on_conflict = on_conflict
        return self
    def execute(self):
        return SimpleNamespace(data=self.data)


class Client:
    def __init__(self, data=None):
        self.query = Query(data)
    def table(self, name):
        self.table_name = name
        return self.query


def test_entitlement_read_is_scoped_to_authenticated_user():
    client = Client({"status": "active"})
    assert premium_access.get_entitlement(client, User()) == {"status": "active"}
    assert client.table_name == "sowia_entitlements"
    assert ("user_id", "user-123") in client.query.filters


def test_entitlement_read_requires_login():
    with pytest.raises(PermissionError):
        premium_access.get_entitlement(Client(), None)


def test_entitlement_grant_uses_admin_upsert_and_user_id():
    client = Client([])
    premium_access.grant_paypal_entitlement(client, "user-123", "ORDER-1", "12.90", "EUR")
    assert client.query.on_conflict == "user_id"
    assert client.query.payload["user_id"] == "user-123"
    assert client.query.payload["paypal_order_id"] == "ORDER-1"
    assert client.query.payload["status"] == "active"


def test_entitlement_grant_rejects_missing_admin_client():
    with pytest.raises(RuntimeError):
        premium_access.grant_paypal_entitlement(None, "user-123", "ORDER-1", "12.90", "EUR")


@pytest.mark.parametrize("amount", ["0", "-1", "NaN", "Infinity", "10000.00", "not-a-number"])
def test_entitlement_grant_rejects_invalid_amount_before_database_write(amount):
    client = Client([])
    with pytest.raises(ValueError):
        premium_access.grant_paypal_entitlement(
            client, "user-123", "ORDER-1", amount, "EUR"
        )
    assert client.query.payload is None


def test_entitlement_grant_normalizes_amount_and_currency():
    client = Client([])
    premium_access.grant_paypal_entitlement(
        client, "user-123", "ORDER-1", "12.9", "eur"
    )
    assert client.query.payload["amount"] == "12.90"
    assert client.query.payload["currency"] == "EUR"


def test_entitlement_grant_rejects_non_euro_currency():
    client = Client([])
    with pytest.raises(ValueError):
        premium_access.grant_paypal_entitlement(
            client, "user-123", "ORDER-1", "12.90", "USD"
        )
    assert client.query.payload is None


@pytest.mark.parametrize(
    "user_id, order_id",
    [(" ", "ORDER-1"), ("user-123", " ")],
)
def test_entitlement_grant_rejects_blank_identity_fields(user_id, order_id):
    client = Client([])
    with pytest.raises(ValueError):
        premium_access.grant_paypal_entitlement(
            client, user_id, order_id, "12.90", "EUR"
        )
    assert client.query.payload is None



@pytest.mark.parametrize(
    "entitlement",
    [None, {"status": "inactive"}, {"status": "pending"}],
)
def test_premium_guard_denies_missing_or_inactive_entitlement(entitlement):
    client = Client(entitlement)
    with pytest.raises(PermissionError, match="accès SOW IA Premium actif"):
        premium_access.require_active_entitlement(client, User())


def test_premium_guard_returns_active_entitlement():
    active = {
        "status": "active",
        "provider": "paypal",
        "amount": "12.90",
        "currency": "EUR",
    }
    assert premium_access.require_active_entitlement(Client(active), User()) == active


def test_premium_guard_requires_authenticated_user():
    with pytest.raises(PermissionError, match="Connexion requise"):
        premium_access.require_active_entitlement(Client(), None)



@pytest.mark.parametrize(
    "user, expected",
    [
        (SimpleNamespace(app_metadata={"sowia_admin": True}), True),
        (SimpleNamespace(app_metadata={"role": "admin"}), True),
        (SimpleNamespace(app_metadata={"sowia_admin": False, "role": "user"}), False),
        (SimpleNamespace(app_metadata={}), False),
        (SimpleNamespace(app_metadata=None), False),
        (SimpleNamespace(app_metadata="admin"), False),
        (SimpleNamespace(user_metadata={"sowia_admin": True}), False),
        (None, False),
    ],
)
def test_sowia_admin_requires_server_managed_app_metadata(user, expected):
    assert premium_access.is_sowia_admin(user) is expected

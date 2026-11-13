"""Unit tests for the NIGHT EXCHANGE bilateral-offer client helpers."""
from types import SimpleNamespace

import pytest
import cloud_storage


class User:
    id = "user-123"

    def __init__(self, app_metadata=None):
        self.app_metadata = app_metadata or {}


class RpcCall:
    def __init__(self, name, params, result):
        self.name = name
        self.params = params
        self.result = result

    def execute(self):
        return self.result


class RpcClient:
    def __init__(self, result=None):
        self.result = SimpleNamespace(data=result)
        self.calls = []

    def rpc(self, name, params):
        call = RpcCall(name, params, self.result)
        self.calls.append(call)
        return call


class Query:
    def __init__(self, result=None):
        self.result = SimpleNamespace(data=result or [])
        self.filters = []
        self.operations = []

    def select(self, columns):
        self.operations.append(("select", columns))
        return self

    def eq(self, field, value):
        self.filters.append((field, value))
        return self

    def order(self, field, desc=False):
        self.operations.append(("order", field, desc))
        return self

    def limit(self, value):
        self.operations.append(("limit", value))
        return self

    def execute(self):
        return self.result


class TableClient:
    def __init__(self):
        self.queries = []

    def table(self, name):
        query = Query()
        self.queries.append((name, query))
        return query


def test_create_offer_calls_guarded_rpc_with_trimmed_summary():
    client = RpcClient(result="offer-1")
    result = cloud_storage.create_night_exchange_offer(
        client, User(), "app-a", "app-b", "  Collaboration API  "
    )
    assert result == "offer-1"
    assert client.calls[0].name == "sowia_nex_create_offer"
    assert client.calls[0].params == {
        "p_sender_app_id": "app-a",
        "p_recipient_app_id": "app-b",
        "p_offer_summary": "Collaboration API",
    }


@pytest.mark.parametrize("summary", ["too short", "x" * 2001, "   "])
def test_create_offer_rejects_invalid_summary_before_rpc(summary):
    client = RpcClient()
    with pytest.raises(ValueError):
        cloud_storage.create_night_exchange_offer(
            client, User(), "app-a", "app-b", summary
        )
    assert client.calls == []


def test_create_offer_rejects_same_or_missing_application_ids_before_rpc():
    client = RpcClient()
    for sender, recipient in [("same", "same"), (None, "app-b"), ("app-a", "")]:
        with pytest.raises(ValueError):
            cloud_storage.create_night_exchange_offer(
                client, User(), sender, recipient, "Valid collaboration"
            )
    assert client.calls == []


@pytest.mark.parametrize("decision", ["accepted", "rejected"])
def test_respond_offer_uses_guarded_rpc(decision):
    client = RpcClient(result={"ok": True})
    cloud_storage.respond_night_exchange_offer(client, User(), "offer-1", decision)
    assert client.calls[0].name == "sowia_nex_respond_offer"
    assert client.calls[0].params == {
        "p_offer_id": "offer-1",
        "p_decision": decision,
    }


def test_respond_offer_rejects_invalid_decision_before_rpc():
    client = RpcClient()
    with pytest.raises(ValueError):
        cloud_storage.respond_night_exchange_offer(
            client, User(), "offer-1", "pending"
        )
    assert client.calls == []


def test_list_my_offers_scopes_both_queries_to_authenticated_user_and_professional_workspace():
    client = TableClient()
    assert cloud_storage.list_my_night_exchange_offers(client, User()) == []
    assert [name for name, _ in client.queries] == [
        "sowia_night_exchange_offers",
        "sowia_night_exchange_offers",
    ]
    for _, query in client.queries:
        assert ("workspace_id", "professional") in query.filters
    assert ("sender_user_id", "user-123") in client.queries[0][1].filters
    assert ("recipient_user_id", "user-123") in client.queries[1][1].filters


def test_admin_integration_queue_rejects_non_admin_before_rpc():
    client = RpcClient()
    with pytest.raises(PermissionError, match="administrateur"):
        cloud_storage.list_night_exchange_integrations_for_admin(client, User())
    assert client.calls == []


@pytest.mark.parametrize("metadata", [{"sowia_admin": True}, {"role": "admin"}])
def test_admin_integration_queue_uses_signed_admin_rpc(metadata):
    client = RpcClient(result=[{"id": "offer-1"}])
    result = cloud_storage.list_night_exchange_integrations_for_admin(
        client, User(metadata)
    )
    assert result == [{"id": "offer-1"}]
    assert client.calls[0].name == "sowia_admin_list_nex_integrations"


def test_admin_review_rejects_non_admin_and_invalid_decisions_before_rpc():
    client = RpcClient()
    with pytest.raises(PermissionError):
        cloud_storage.admin_review_night_exchange_integration(
            client, User(), "offer-1", "approved"
        )
    with pytest.raises(ValueError):
        cloud_storage.admin_review_night_exchange_integration(
            client, User({"role": "admin"}), "offer-1", "pending"
        )
    with pytest.raises(ValueError):
        cloud_storage.admin_review_night_exchange_integration(
            client, User({"role": "admin"}), "offer-1", "approved", "x" * 1001
        )
    assert client.calls == []


@pytest.mark.parametrize("decision", ["approved", "rejected"])
def test_admin_review_calls_guarded_rpc_for_valid_admin_decision(decision):
    client = RpcClient(result={"ok": True})
    cloud_storage.admin_review_night_exchange_integration(
        client, User({"sowia_admin": True}), "offer-1", decision, "Reviewed"
    )
    assert client.calls[0].name == "sowia_admin_review_nex_integration"
    assert client.calls[0].params == {
        "p_offer_id": "offer-1",
        "p_decision": decision,
        "p_review_note": "Reviewed",
    }

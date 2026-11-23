"""Client helper tests for the NIGHT EXCHANGE commercial register."""
from types import SimpleNamespace

import pytest
import cloud_storage


class User:
    id = "member-1"


class RpcCall:
    def __init__(self, name, params, result):
        self.name = name
        self.params = params
        self.result = result

    def execute(self):
        return SimpleNamespace(data=self.result)


class RpcClient:
    def __init__(self, result="deal-1"):
        self.result = result
        self.calls = []

    def rpc(self, name, params):
        call = RpcCall(name, params, self.result)
        self.calls.append(call)
        return call


class Query:
    def __init__(self, rows=None):
        self.rows = rows or []
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
        return SimpleNamespace(data=self.rows)


class TableClient:
    def __init__(self, responses=None):
        self.responses = list(responses or [])
        self.queries = []

    def table(self, name):
        rows = self.responses.pop(0) if self.responses else []
        query = Query(rows)
        self.queries.append((name, query))
        return query


def test_create_deal_calls_server_rpc_and_normalizes_amount():
    client = RpcClient()
    result = cloud_storage.create_night_exchange_deal(
        client, User(), "app-a", "app-b", "  Contrat API  ",
        "Conditions", "monetary", "125.5", "eur", 500, "request-key-123456",
    )
    assert result == "deal-1"
    assert client.calls[0].name == "sowia_nex_create_deal"
    assert client.calls[0].params == {
        "p_creator_app_id": "app-a",
        "p_counterparty_app_id": "app-b",
        "p_title": "Contrat API",
        "p_description": "Conditions",
        "p_deal_kind": "monetary",
        "p_agreed_amount": "125.50",
        "p_currency": "EUR",
        "p_commission_bps": 500,
        "p_idempotency_key": "request-key-123456",
    }


@pytest.mark.parametrize("kwargs", [
    {"creator_app_id": "same", "counterparty_app_id": "same"},
    {"title": "x"},
    {"title": "Contrat valide", "deal_kind": "non_monetary", "agreed_amount": "1", "commission_bps": 0},
    {"title": "Contrat valide", "deal_kind": "non_monetary", "agreed_amount": "0", "commission_bps": 1},
    {"title": "Contrat valide", "agreed_amount": "-1"},
    {"title": "Contrat valide", "currency": "EURO"},
])
def test_create_deal_rejects_invalid_input_before_rpc(kwargs):
    client = RpcClient()
    params = {
        "creator_app_id": "app-a",
        "counterparty_app_id": "app-b",
        "title": "Contrat valide",
        "description": "",
        "deal_kind": "monetary",
        "agreed_amount": "10",
        "currency": "EUR",
        "commission_bps": 0,
        "idempotency_key": "request-key-123456",
    }
    params.update(kwargs)
    with pytest.raises(ValueError):
        cloud_storage.create_night_exchange_deal(client, User(), **params)
    assert client.calls == []


def test_list_deals_scopes_both_queries_to_current_user_and_deduplicates():
    client = TableClient([
        [{"id": "deal-a", "created_at": "2026-01-02"}],
        [{"id": "deal-a", "created_at": "2026-01-02"}, {"id": "deal-b", "created_at": "2026-01-01"}],
    ])
    rows = cloud_storage.list_my_night_exchange_deals(client, User())
    assert [row["id"] for row in rows] == ["deal-a", "deal-b"]
    assert [name for name, _ in client.queries] == ["sowia_nex_deals", "sowia_nex_deals"]
    assert ("created_by", "member-1") in client.queries[0][1].filters
    assert ("counterparty_user_id", "member-1") in client.queries[1][1].filters


def test_list_deal_events_is_scoped_to_deal_id():
    client = TableClient([[{"id": "event-1"}]])
    assert cloud_storage.list_night_exchange_deal_events(client, User(), "deal-1") == [{"id": "event-1"}]
    assert client.queries[0][0] == "sowia_nex_deal_events"
    assert ("deal_id", "deal-1") in client.queries[0][1].filters


def test_transition_calls_guarded_rpc_with_idempotency_key():
    client = RpcClient(result="event-1")
    result = cloud_storage.transition_night_exchange_deal(
        client, User(), "deal-1", "accepted", "transition-key-1234", "Approved",
    )
    assert result == "event-1"
    assert client.calls[0].name == "sowia_nex_transition_deal"
    assert client.calls[0].params == {
        "p_deal_id": "deal-1",
        "p_target_status": "accepted",
        "p_idempotency_key": "transition-key-1234",
        "p_note": "Approved",
    }


def test_transition_rejects_invalid_request_before_rpc():
    client = RpcClient()
    with pytest.raises(ValueError):
        cloud_storage.transition_night_exchange_deal(
            client, User(), "deal-1", "payment_confirmed", "transition-key-1234",
        )
    assert client.calls == []

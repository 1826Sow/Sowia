from types import SimpleNamespace
import uuid

import pytest

from agent_data_rights import (
    delete_agent_conversation,
    delete_private_agent_memory,
    list_private_agent_memories,
)


class Result:
    def __init__(self, data):
        self.data = data


class Query:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.filters = []
        self.deleted = False

    def select(self, fields): return self
    def eq(self, key, value):
        self.filters.append((key, value))
        return self
    def order(self, *args, **kwargs): return self
    def limit(self, *args): return self
    def delete(self):
        self.deleted = True
        return self
    def execute(self): return Result(self.rows)


class Client:
    def __init__(self, rows=None, rpc_data=True):
        self.rows = rows or {}
        self.rpc_data = rpc_data
        self.queries = []
        self.rpc_calls = []
    def table(self, name):
        q = Query(self.rows.get(name, []))
        self.queries.append((name, q))
        return q
    def rpc(self, name, params):
        self.rpc_calls.append((name, params))
        return Result(self.rpc_data)


def test_list_private_memories_is_scoped_to_owner_agent_and_workspace():
    agent = str(uuid.uuid4())
    client = Client({"sowia_agents": [{"id": agent}], "sowia_agent_memory_items": [{"id": 3}]})
    rows = list_private_agent_memories(client, SimpleNamespace(id="owner"), agent, "professional")
    assert rows == [{"id": 3}]
    filters = client.queries[-1][1].filters
    assert ("user_id", "owner") in filters
    assert ("agent_id", agent) in filters
    assert ("workspace_id", "professional") in filters


def test_delete_memory_requires_exact_owned_row():
    agent = str(uuid.uuid4())
    client = Client({"sowia_agent_memory_items": [{"id": 9}]})
    assert delete_private_agent_memory(client, SimpleNamespace(id="owner"), agent, 9) is True
    name, query = client.queries[0]
    assert query.deleted
    assert ("user_id", "owner") in query.filters
    assert ("agent_id", agent) in query.filters
    assert ("id", 9) in query.filters


def test_delete_memory_refuses_missing_row():
    with pytest.raises(PermissionError):
        delete_private_agent_memory(Client(), SimpleNamespace(id="owner"), str(uuid.uuid4()), 9)


def test_delete_agent_conversation_calls_owner_checked_rpc():
    agent, conversation = str(uuid.uuid4()), str(uuid.uuid4())
    client = Client(rpc_data=True)
    assert delete_agent_conversation(client, SimpleNamespace(id="owner"), agent, conversation, "personal")
    assert client.rpc_calls == [("sowia_delete_my_agent_conversation", {
        "p_agent_id": agent, "p_conversation_id": conversation, "p_workspace_id": "personal"
    })]


def test_delete_agent_conversation_requires_rpc_confirmation():
    with pytest.raises(PermissionError):
        delete_agent_conversation(Client(rpc_data=False), SimpleNamespace(id="owner"), str(uuid.uuid4()), str(uuid.uuid4()))

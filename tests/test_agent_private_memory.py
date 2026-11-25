"""Tests for owner-controlled agent registry and private memory."""
from types import SimpleNamespace

import pytest

import cloud_storage
from memory_access import (
    add_agent_memory,
    load_agent_memory_context,
    register_agent,
    update_agent_memory_permissions,
)


class Query:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.filters = []
        self.inserted = None
        self.updated = None

    def select(self, fields): return self
    def eq(self, key, value):
        self.filters.append((key, value))
        return self
    def is_(self, key, value):
        self.filters.append((key, value))
        return self
    def order(self, *args, **kwargs): return self
    def limit(self, count): return self
    def insert(self, payload):
        self.inserted = payload
        return self
    def update(self, payload):
        self.updated = payload
        return self
    def execute(self):
        return SimpleNamespace(data=self.rows)


class Client:
    def __init__(self, table_rows):
        self.table_rows = table_rows
        self.queries = {}

    def table(self, name):
        query = Query(self.table_rows.get(name, []))
        self.queries[name] = query
        return query


def test_register_agent_binds_owner_and_defaults_to_no_shared_memory():
    client = Client({"sowia_agents": [{"id": "agent-uuid", "name": "Agent API"}]})
    agent = register_agent(client, SimpleNamespace(id="user-1"), "Agent API")
    payload = client.queries["sowia_agents"].inserted
    assert payload["user_id"] == "user-1"
    assert payload["can_read_workspace_memory"] is False
    assert payload["can_read_project_memory"] is False
    assert payload["can_write_private_memory"] is True
    assert agent["id"] == "agent-uuid"


def test_agent_memory_write_requires_owned_active_agent():
    client = Client({"sowia_agents": [{"id": "agent-1"}],
                     "sowia_agent_memory_items": [{"id": 9, "content": "note"}]})
    add_agent_memory(client, SimpleNamespace(id="user-1"), "agent-1", "note")
    assert client.queries["sowia_agents"].filters == [
        ("id", "agent-1"), ("user_id", "user-1"),
        ("workspace_id", "personal"), ("status", "active"),
        ("can_write_private_memory", True),
    ]
    assert client.queries["sowia_agent_memory_items"].inserted["user_id"] == "user-1"


def test_agent_context_only_reads_shared_memory_when_granted(monkeypatch):
    client = Client({
        "sowia_agents": [{
            "id": "agent-1", "project_id": 42,
            "can_read_workspace_memory": False,
            "can_read_project_memory": False, "status": "active",
        }],
        "sowia_agent_memory_items": [{"content": "Note privée agent"}],
    })
    monkeypatch.setattr(cloud_storage, "list_memories",
                        lambda *args: pytest.fail("Shared memory must not be queried"))
    result = load_agent_memory_context(
        client, SimpleNamespace(id="user-1"), "agent-1"
    )
    assert result == ["Note privée agent"]


def test_agent_context_reads_only_explicitly_granted_project(monkeypatch):
    client = Client({
        "sowia_agents": [{
            "id": "agent-1", "project_id": 42,
            "can_read_workspace_memory": False,
            "can_read_project_memory": True, "status": "active",
        }],
        "sowia_agent_memory_items": [{"content": "Note privée agent"}],
    })
    monkeypatch.setattr(cloud_storage, "list_memories", lambda *args: [
        {"content": "Projet autorisé", "project_id": 42},
        {"content": "Projet interdit", "project_id": 43},
        {"content": "Note générale", "project_id": None},
    ])
    result = load_agent_memory_context(
        client, SimpleNamespace(id="user-1"), "agent-1"
    )
    assert result == ["Note privée agent", "Projet autorisé"]


def test_owner_can_revoke_agent_memory_permissions():
    client = Client({"sowia_agents": [{"id": "agent-1"}]})
    update_agent_memory_permissions(
        client, SimpleNamespace(id="user-1"), "agent-1",
        can_read_project_memory=False,
    )
    assert client.queries["sowia_agents"].updated == {
        "can_read_project_memory": False
    }
    assert ("user_id", "user-1") in client.queries["sowia_agents"].filters


@pytest.mark.parametrize("bad", ["yes", 1, None])
def test_permissions_are_boolean_or_omitted(bad):
    if bad is None:
        return
    with pytest.raises(ValueError):
        update_agent_memory_permissions(
            Client({}), SimpleNamespace(id="user-1"), "agent-1",
            can_read_project_memory=bad,
        )

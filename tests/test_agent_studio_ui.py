from types import SimpleNamespace

import pytest

from agent_studio_ui import _set_agent_status


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows
        self.filters = []

    def update(self, payload):
        self.payload = payload
        return self

    def eq(self, key, value):
        self.filters.append(("eq", key, value))
        return self

    def in_(self, key, values):
        self.filters.append(("in", key, values))
        return self

    def execute(self):
        return SimpleNamespace(data=self.rows)


class FakeClient:
    def __init__(self, rows):
        self.query = FakeQuery(rows)

    def table(self, name):
        assert name == "sowia_agents"
        return self.query


def test_set_agent_status_scopes_update_to_owner_and_workspace():
    client = FakeClient([{"id": "agent-1", "status": "paused"}])
    user = SimpleNamespace(id="owner-1")
    agent = {"id": "agent-1"}

    result = _set_agent_status(client, user, agent, "personal", "paused")

    assert result["status"] == "paused"
    assert client.query.payload == {"status": "paused"}
    assert ("eq", "id", "agent-1") in client.query.filters
    assert ("eq", "user_id", "owner-1") in client.query.filters
    assert ("eq", "workspace_id", "personal") in client.query.filters
    assert ("in", "status", ["active", "paused"]) in client.query.filters


def test_set_agent_status_rejects_unapproved_status():
    client = FakeClient([{"id": "agent-1"}])
    user = SimpleNamespace(id="owner-1")

    with pytest.raises(ValueError):
        _set_agent_status(client, user, {"id": "agent-1"}, "personal", "archived")


def test_set_agent_status_requires_confirmed_update():
    client = FakeClient([])
    user = SimpleNamespace(id="owner-1")

    with pytest.raises(PermissionError):
        _set_agent_status(client, user, {"id": "agent-1"}, "personal", "paused")

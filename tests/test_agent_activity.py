"""Tests for owner-scoped per-agent activity history."""
import uuid
from types import SimpleNamespace

import pytest

from agent_usage_quota import get_agent_activity, finish_agent_action


OWNER = SimpleNamespace(id="owner-1")
AGENT = "00000000-0000-0000-0000-000000000001"
REQUEST = "00000000-0000-0000-0000-000000000002"


class Rpc:
    def __init__(self, data):
        self.data = data

    def execute(self):
        return SimpleNamespace(data=self.data)


class Client:
    def __init__(self, data=True):
        self.data = data
        self.calls = []

    def rpc(self, name, params):
        self.calls.append((name, params))
        return Rpc(self.data)


def test_get_agent_activity_returns_lifetime_totals_and_recent_events():
    row = {
        "total_credits": 11,
        "total_actions": 4,
        "request_id": REQUEST,
        "tool_name": "web_search",
        "action": "web_search",
        "credits": 3,
        "status": "completed",
        "error_code": None,
        "created_at": "2026-11-25T10:00:00Z",
        "finished_at": "2026-11-25T10:00:01Z",
        "used_after": 11,
    }
    client = Client([row])
    result = get_agent_activity(client, OWNER, AGENT, limit=10)

    assert result["total_credits"] == 11
    assert result["total_actions"] == 4
    assert result["events"] == [row]
    assert client.calls[0][0] == "sowia_get_agent_activity"
    assert client.calls[0][1] == {"p_agent_id": AGENT, "p_limit": 10}


def test_get_agent_activity_handles_empty_history():
    result = get_agent_activity(Client([]), OWNER, AGENT)
    assert result == {"total_credits": 0, "total_actions": 0, "events": []}


@pytest.mark.parametrize("agent_id", ["not-a-uuid", None])
def test_get_agent_activity_rejects_invalid_agent_id(agent_id):
    client = Client([])
    with pytest.raises(ValueError):
        get_agent_activity(client, OWNER, agent_id)
    assert client.calls == []


def test_get_agent_activity_rejects_out_of_range_limit():
    client = Client([])
    with pytest.raises(ValueError):
        get_agent_activity(client, OWNER, AGENT, limit=1000)
    assert client.calls == []


def test_finish_agent_action_uses_owner_authenticated_rpc():
    client = Client(True)
    result = finish_agent_action(client, OWNER, REQUEST, AGENT, "completed")

    assert result is True
    assert client.calls[0][0] == "sowia_finish_agent_action_for_agent"
    assert client.calls[0][1]["p_request_id"] == REQUEST
    assert client.calls[0][1]["p_agent_id"] == AGENT
    assert client.calls[0][1]["p_status"] == "completed"


def test_finish_agent_action_rejects_invalid_status_before_rpc():
    client = Client()
    with pytest.raises(ValueError):
        finish_agent_action(client, OWNER, REQUEST, AGENT, "deleted")
    assert client.calls == []

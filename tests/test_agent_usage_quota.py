"""Tests for persistent agent quota RPC adapter."""
import uuid
from types import SimpleNamespace

import pytest

from agent_usage_quota import consume_agent_action, get_agent_usage


class FakeRpc:
    def __init__(self, data):
        self.data = data

    def execute(self):
        return SimpleNamespace(data=self.data)


class FakeClient:
    def __init__(self, data):
        self.data = data
        self.calls = []

    def rpc(self, name, params):
        self.calls.append((name, params))
        return FakeRpc(self.data)


def test_get_agent_usage_uses_authenticated_client_rpc():
    client = FakeClient([{
        "month_start": "2026-11-01",
        "used_credits": 27,
        "monthly_limit": 1000,
        "remaining_credits": 973,
    }])
    result = get_agent_usage(client, SimpleNamespace(id="user-1"))
    assert result["used_credits"] == 27
    assert result["remaining_credits"] == 973
    assert client.calls == [("sowia_get_agent_usage", {})]


def test_consume_agent_action_sends_action_and_idempotency_uuid_only():
    request_id = str(uuid.uuid4())
    client = FakeClient([{
        "allowed": True,
        "used_credits": 5,
        "monthly_limit": 1000,
        "remaining_credits": 995,
        "reason": "quota_available",
    }])
    result = consume_agent_action(
        client, SimpleNamespace(id="user-1"), "code_generation", request_id
    )
    assert result["allowed"] is True
    assert result["requested_credits"] == 5
    assert client.calls == [(
        "sowia_consume_agent_credits",
        {"p_request_id": request_id, "p_action": "code_generation"},
    )]
    assert "user_id" not in client.calls[0][1]
    assert "p_credits" not in client.calls[0][1]


def test_quota_denial_is_returned_without_attempting_payment():
    client = FakeClient([{
        "allowed": False,
        "used_credits": 999,
        "monthly_limit": 1000,
        "remaining_credits": 1,
        "reason": "quota_exceeded",
    }])
    result = consume_agent_action(
        client, SimpleNamespace(id="user-1"), "web_search", str(uuid.uuid4())
    )
    assert result["allowed"] is False
    assert result["reason"] == "quota_exceeded"


def test_missing_user_is_rejected_before_rpc():
    client = FakeClient([])
    with pytest.raises(PermissionError):
        get_agent_usage(client, SimpleNamespace(id=None))
    assert client.calls == []


def test_unknown_action_is_rejected_before_rpc():
    client = FakeClient([])
    with pytest.raises(ValueError):
        consume_agent_action(
            client, SimpleNamespace(id="user-1"), "unpriced_action", str(uuid.uuid4())
        )
    assert client.calls == []


def test_invalid_idempotency_key_is_rejected():
    client = FakeClient([])
    with pytest.raises(ValueError):
        consume_agent_action(client, SimpleNamespace(id="user-1"), "chat", "not-a-uuid")
    assert client.calls == []


def test_missing_rpc_result_fails_closed():
    client = FakeClient(None)
    with pytest.raises(RuntimeError):
        consume_agent_action(
            client, SimpleNamespace(id="user-1"), "chat", str(uuid.uuid4())
        )


def test_agent_action_uses_owner_scoped_agent_activity_rpc():
    request_id = str(uuid.uuid4())
    agent_id = "00000000-0000-0000-0000-000000000001"
    client = FakeClient([{
        "allowed": True,
        "used_credits": 1,
        "monthly_limit": 1000,
        "remaining_credits": 999,
        "reason": "quota_available",
    }])
    result = consume_agent_action(
        client, SimpleNamespace(id="user-1"), "chat", request_id,
        agent_id=agent_id, workspace_id="personal", tool_name="agent_chat",
    )
    assert result["allowed"] is True
    assert client.calls == [(
        "sowia_consume_agent_action_for_agent",
        {
            "p_request_id": request_id,
            "p_action": "chat",
            "p_agent_id": agent_id,
            "p_workspace_id": "personal",
            "p_tool_name": "agent_chat",
        },
    )]


def test_agent_action_rejects_tool_action_mismatch_before_rpc():
    client = FakeClient([])
    with pytest.raises(ValueError):
        consume_agent_action(
            client, SimpleNamespace(id="user-1"), "chat", str(uuid.uuid4()),
            agent_id="00000000-0000-0000-0000-000000000001",
            workspace_id="personal", tool_name="web_search",
        )
    assert client.calls == []

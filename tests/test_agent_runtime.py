"""Tests for the common agent execution quota gate."""
import uuid
from types import SimpleNamespace

import pytest

from agent_runtime import AgentQuotaExceeded, execute_agent_action


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


def _allowed_client():
    return FakeClient([{
        "allowed": True,
        "used_credits": 5,
        "monthly_limit": 1000,
        "remaining_credits": 995,
        "reason": "quota_available",
    }])


def test_allowed_action_consumes_quota_then_calls_server_handler_once():
    client = _allowed_client()
    calls = []

    def handler(value, suffix="!"):
        calls.append((value, suffix))
        return value + suffix

    result = execute_agent_action(
        client, SimpleNamespace(id="user-1"), "code_generation",
        str(uuid.uuid4()), handler, "generated", suffix=" ok",
    )

    assert result["result"] == "generated ok"
    assert result["usage"]["requested_credits"] == 5
    assert calls == [("generated", " ok")]
    assert len(client.calls) == 1
    assert client.calls[0][0] == "sowia_consume_agent_credits"


def test_quota_denial_never_calls_handler():
    client = FakeClient([{
        "allowed": False,
        "used_credits": 999,
        "monthly_limit": 1000,
        "remaining_credits": 1,
        "reason": "quota_exceeded",
    }])
    calls = []

    with pytest.raises(AgentQuotaExceeded) as exc:
        execute_agent_action(
            client, SimpleNamespace(id="user-1"), "web_search",
            str(uuid.uuid4()), lambda: calls.append("ran"),
        )

    assert exc.value.usage["reason"] == "quota_exceeded"
    assert calls == []


def test_handler_must_be_a_server_callable():
    client = _allowed_client()
    with pytest.raises(TypeError):
        execute_agent_action(
            client, SimpleNamespace(id="user-1"), "chat",
            str(uuid.uuid4()), "client-supplied-handler",
        )
    assert client.calls == []


def test_handler_error_propagates_after_one_quota_debit():
    client = _allowed_client()

    def failing_handler():
        raise RuntimeError("tool failed")

    with pytest.raises(RuntimeError, match="tool failed"):
        execute_agent_action(
            client, SimpleNamespace(id="user-1"), "tool_execution",
            str(uuid.uuid4()), failing_handler,
        )
    assert len(client.calls) == 1


def test_missing_authenticated_user_fails_before_handler():
    client = _allowed_client()
    calls = []
    with pytest.raises(PermissionError):
        execute_agent_action(
            client, SimpleNamespace(id=None), "chat",
            str(uuid.uuid4()), lambda: calls.append("ran"),
        )
    assert client.calls == []
    assert calls == []


def test_agent_action_records_agent_attribution_and_completion():
    client = _allowed_client()
    agent_id = "00000000-0000-0000-0000-000000000001"
    request_id = str(uuid.uuid4())
    result = execute_agent_action(
        client, SimpleNamespace(id="user-1"), "web_search",
        request_id, lambda: "found",
        agent_id=agent_id, workspace_id="personal", tool_name="web_search",
    )
    assert result["result"] == "found"
    assert client.calls[0][0] == "sowia_consume_agent_action_for_agent"
    assert client.calls[0][1]["p_agent_id"] == agent_id
    assert client.calls[0][1]["p_tool_name"] == "web_search"
    assert client.calls[1][0] == "sowia_finish_agent_action_for_agent"
    assert client.calls[1][1]["p_status"] == "completed"


def test_agent_action_records_failure_without_leaking_error_message():
    client = _allowed_client()
    agent_id = "00000000-0000-0000-0000-000000000001"
    request_id = str(uuid.uuid4())

    def fail():
        raise RuntimeError("sensitive provider details")

    with pytest.raises(RuntimeError, match="sensitive provider details"):
        execute_agent_action(
            client, SimpleNamespace(id="user-1"), "tool_execution",
            request_id, fail,
            agent_id=agent_id, workspace_id="personal", tool_name="memory_read",
        )
    assert client.calls[1][0] == "sowia_finish_agent_action_for_agent"
    assert client.calls[1][1]["p_status"] == "failed"
    assert client.calls[1][1]["p_error_code"] == "RuntimeError"


def test_agent_action_rejects_missing_activity_metadata_before_debit():
    client = _allowed_client()
    with pytest.raises(ValueError):
        execute_agent_action(
            client, SimpleNamespace(id="user-1"), "tool_execution",
            str(uuid.uuid4()), lambda: "no",
            agent_id="00000000-0000-0000-0000-000000000001",
            workspace_id="personal",
        )
    assert client.calls == []

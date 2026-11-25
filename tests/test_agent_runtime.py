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

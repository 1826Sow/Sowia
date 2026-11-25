"""Tests for the allowlisted SOW IA agent tool registry."""
import uuid
from types import SimpleNamespace

import pytest

import agent_tools
from agent_tools import AgentToolError, execute_registered_agent_tool, list_agent_tools


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


def _client(allowed=True):
    return FakeClient([{
        "allowed": allowed,
        "used_credits": 3,
        "monthly_limit": 1000,
        "remaining_credits": 997 if allowed else 0,
        "reason": "quota_available" if allowed else "quota_exceeded",
    }])


def test_registry_exposes_only_public_schema_not_handlers():
    tools = list_agent_tools()
    assert [item["name"] for item in tools] == ["web_search"]
    assert tools[0]["input_schema"]["additionalProperties"] is False
    assert "handler" not in tools[0]


def test_web_search_is_quota_gated_and_normalized(monkeypatch):
    client = _client()
    monkeypatch.setattr(agent_tools, "_web_search_handler", lambda *a, **k: [])
    # Replace the registered server handler for this isolated test.
    monkeypatch.setitem(agent_tools._TOOL_REGISTRY["web_search"], "handler",
                        lambda query, max_results=5: [{
                            "title": "Example", "url": "https://example.test", "content": "Found"
                        }])
    result = execute_registered_agent_tool(
        client, SimpleNamespace(id="owner-1"), "web_search", str(uuid.uuid4()),
        {"query": "latest AI", "max_results": 3},
    )
    assert result["result"][0]["url"] == "https://example.test"
    assert result["usage"]["requested_credits"] == 3
    assert client.calls[0][0] == "sowia_consume_agent_credits"


def test_unknown_tool_is_rejected_before_quota_call():
    client = _client()
    with pytest.raises(AgentToolError):
        execute_registered_agent_tool(
            client, SimpleNamespace(id="owner-1"), "run_python", str(uuid.uuid4()), {}
        )
    assert client.calls == []


def test_client_cannot_supply_handler_or_extra_arguments():
    client = _client()
    with pytest.raises(AgentToolError):
        execute_registered_agent_tool(
            client, SimpleNamespace(id="owner-1"), "web_search", str(uuid.uuid4()),
            {"query": "hello", "handler": "os.system"},
        )
    assert client.calls == []


@pytest.mark.parametrize("arguments", [
    {},
    {"query": ""},
    {"query": "x" * 501},
    {"query": "valid", "max_results": True},
    {"query": "valid", "max_results": 11},
    ["valid"],
])
def test_invalid_arguments_are_rejected_before_quota_call(arguments):
    client = _client()
    with pytest.raises(AgentToolError):
        execute_registered_agent_tool(
            client, SimpleNamespace(id="owner-1"), "web_search", str(uuid.uuid4()), arguments
        )
    assert client.calls == []


def test_quota_denial_blocks_web_search_handler(monkeypatch):
    client = _client(allowed=False)
    calls = []
    monkeypatch.setitem(agent_tools._TOOL_REGISTRY["web_search"], "handler",
                        lambda *a, **k: calls.append("ran"))
    from agent_runtime import AgentQuotaExceeded
    with pytest.raises(AgentQuotaExceeded):
        execute_registered_agent_tool(
            client, SimpleNamespace(id="owner-1"), "web_search", str(uuid.uuid4()),
            {"query": "latest AI"},
        )
    assert calls == []
    assert len(client.calls) == 1

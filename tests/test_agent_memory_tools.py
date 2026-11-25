"""Tests for quota-gated persistent agent memory tools."""
import sys
import types
import uuid
from types import SimpleNamespace

import pytest

import agent_memory_tools
from agent_memory_tools import (
    AgentMemoryToolError, execute_registered_agent_memory_tool,
    list_agent_memory_tools,
)
from agent_runtime import AgentQuotaExceeded


class Rpc:
    def __init__(self, data): self.data = data
    def execute(self): return SimpleNamespace(data=self.data)


class Client:
    def __init__(self, allowed=True):
        self.allowed = allowed
        self.calls = []
    def rpc(self, name, params):
        self.calls.append((name, params))
        return Rpc([{
            "allowed": self.allowed, "used_credits": 2,
            "monthly_limit": 1000, "remaining_credits": 998,
            "reason": "quota_available" if self.allowed else "quota_exceeded",
        }])


def _memory_module(read=None, write=None):
    return types.SimpleNamespace(
        load_agent_memory_context=read or (lambda *a, **k: ["private note"]),
        add_agent_memory=write or (lambda *a, **k: [{"id": 7, "content": k.get("workspace_id")}]),
    )


def test_schemas_do_not_expose_callables():
    schemas = list_agent_memory_tools()
    assert {item["name"] for item in schemas} == {"memory_read", "memory_write"}
    assert all(item["input_schema"]["additionalProperties"] is False for item in schemas)


def test_memory_read_is_quota_gated_and_uses_scoped_memory_api(monkeypatch):
    calls = []
    monkeypatch.setitem(sys.modules, "memory_access", _memory_module(
        read=lambda client, user, agent_id, **kw: calls.append((agent_id, kw)) or ["secret note"]
    ))
    client = Client()
    result = execute_registered_agent_memory_tool(
        client, SimpleNamespace(id="owner-1"), "memory_read", str(uuid.uuid4()),
        "00000000-0000-0000-0000-000000000001", "professional", {"query": "API", "max_items": 5},
    )
    assert result["result"] == ["secret note"]
    assert calls[0][0] == "00000000-0000-0000-0000-000000000001"
    assert calls[0][1]["workspace_id"] == "professional"
    assert client.calls[0][0] == "sowia_consume_agent_action_for_agent"


def test_memory_write_is_quota_gated_and_passes_only_bounded_content(monkeypatch):
    calls = []
    monkeypatch.setitem(sys.modules, "memory_access", _memory_module(
        write=lambda client, user, agent_id, content, **kw: calls.append((agent_id, content, kw)) or [{"id": 9}]
    ))
    client = Client()
    result = execute_registered_agent_memory_tool(
        client, SimpleNamespace(id="owner-1"), "memory_write", str(uuid.uuid4()),
        "00000000-0000-0000-0000-000000000001", "personal", {"content": "  conserver cette API  "},
    )
    assert result["result"] == [{"id": 9}]
    assert calls == [("00000000-0000-0000-0000-000000000001", "conserver cette API", {"workspace_id": "personal"})]


def test_quota_denial_prevents_memory_access(monkeypatch):
    calls = []
    monkeypatch.setitem(sys.modules, "memory_access", _memory_module(
        read=lambda *a, **k: calls.append("read")
    ))
    client = Client(allowed=False)
    with pytest.raises(AgentQuotaExceeded):
        execute_registered_agent_memory_tool(
            client, SimpleNamespace(id="owner-1"), "memory_read", str(uuid.uuid4()),
            "00000000-0000-0000-0000-000000000001", arguments={"query": "anything"},
        )
    assert calls == []


@pytest.mark.parametrize("name,args", [
    ("memory_read", {}),
    ("memory_read", {"query": "ok", "max_items": True}),
    ("memory_read", {"query": "ok", "max_chars": 13000}),
    ("memory_read", {"query": "ok", "unexpected": 1}),
    ("memory_write", {}),
    ("memory_write", {"content": "x" * 4001}),
    ("memory_write", {"content": "ok", "extra": True}),
    ("memory_delete", {"id": 1}),
])
def test_invalid_memory_requests_fail_before_quota_or_database(name, args):
    client = Client()
    with pytest.raises(AgentMemoryToolError):
        execute_registered_agent_memory_tool(
            client, SimpleNamespace(id="owner-1"), name, str(uuid.uuid4()),
            "00000000-0000-0000-0000-000000000001", arguments=args,
        )
    assert client.calls == []


def test_invalid_workspace_is_rejected():
    client = Client()
    with pytest.raises(AgentMemoryToolError):
        execute_registered_agent_memory_tool(
            client, SimpleNamespace(id="owner-1"), "memory_read", str(uuid.uuid4()),
            "00000000-0000-0000-0000-000000000001", "shared", {"query": "ok"},
        )
    assert client.calls == []

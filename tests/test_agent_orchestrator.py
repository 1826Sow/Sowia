"""Tests for the bounded SOW IA agent orchestrator."""
import json
from types import SimpleNamespace

import pytest

import agent_orchestrator as orchestrator


class FakeCompletion:
    def __init__(self, message):
        self.choices = [SimpleNamespace(message=message)]


class FakeCompletions:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)


class FakeClient:
    def __init__(self, responses):
        self.chat = SimpleNamespace(completions=FakeCompletions(responses))


def _message(content=None, tool_calls=None):
    return SimpleNamespace(
        content=content,
        tool_calls=tool_calls or [],
        model_dump=lambda **kwargs: {
            "role": "assistant", "content": content,
            "tool_calls": [
                {"id": c.id, "type": "function", "function": {
                    "name": c.function.name, "arguments": c.function.arguments
                }} for c in (tool_calls or [])
            ],
        },
    )


def _call(name, arguments='{"query":"actualité IA"}', call_id="call-1"):
    return SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(name=name, arguments=arguments),
    )


def _setup(monkeypatch, fake_client):
    import sys
    import types
    monkeypatch.setitem(sys.modules, "memory_access", types.SimpleNamespace(
        list_agents=lambda client, user, workspace_id="personal": [
            {"id": "agent-1", "status": "active", "enabled_tools": ["web_search", "memory_read", "memory_write"]}
        ]
    ))
    monkeypatch.setattr(orchestrator, "_provider_configs", lambda: [{
        "api_key": "test", "base_url": "https://example.test", "model": "test"
    }])
    monkeypatch.setattr(orchestrator, "OpenAI", lambda **kwargs: fake_client)
    monkeypatch.setattr(orchestrator, "build_system_prompt", lambda **kwargs: "system")
    monkeypatch.setattr(orchestrator, "consume_agent_action", lambda *a, **k: {
        "allowed": True, "reason": "quota_available"
    })
    monkeypatch.setattr(orchestrator, "finish_agent_action", lambda *a, **k: True)
    monkeypatch.setattr(orchestrator, "_tool_definitions", lambda enabled_tools=None: [{"type": "function"}])


def test_returns_final_answer_without_tools(monkeypatch):
    client = FakeClient([FakeCompletion(_message("Réponse finale"))])
    _setup(monkeypatch, client)
    result = orchestrator.run_agent_turn(
        [{"role": "user", "content": "Bonjour"}],
        user_client=object(), user=SimpleNamespace(id="owner"),
        agent_id="agent-1",
    )
    assert result == "Réponse finale"
    assert client.chat.completions.calls[0]["tool_choice"] == "auto"


def test_dispatches_allowlisted_tool_and_returns_followup(monkeypatch):
    client = FakeClient([
        FakeCompletion(_message(tool_calls=[_call("web_search")])),
        FakeCompletion(_message("Voici le résultat.")),
    ])
    _setup(monkeypatch, client)
    calls = []
    monkeypatch.setattr(orchestrator, "_execute_tool",
                        lambda name, arguments, **kw: calls.append((name, arguments, kw)) or {"result": "ok"})
    result = orchestrator.run_agent_turn(
        [{"role": "user", "content": "Cherche"}],
        user_client=object(), user=SimpleNamespace(id="owner"),
        agent_id="agent-1", request_id="00000000-0000-0000-0000-000000000001",
    )
    assert result == "Voici le résultat."
    assert calls[0][0] == "web_search"
    assert calls[0][2]["request_id"]


def test_rejects_unowned_or_inactive_agent(monkeypatch):
    import sys
    import types
    monkeypatch.setitem(sys.modules, "memory_access", types.SimpleNamespace(
        list_agents=lambda *a, **k: []
    ))
    with pytest.raises(PermissionError):
        orchestrator.run_agent_turn(
            [], user_client=object(), user=SimpleNamespace(id="owner"),
            agent_id="other-agent",
        )


def test_rejects_missing_authenticated_identity():
    with pytest.raises(PermissionError):
        orchestrator.run_agent_turn(
            [], user_client=object(), user=SimpleNamespace(id=None), agent_id="agent-1"
        )


def test_rejects_excessive_tool_rounds(monkeypatch):
    client = FakeClient([FakeCompletion(_message("unused"))])
    _setup(monkeypatch, client)
    with pytest.raises(ValueError):
        orchestrator.run_agent_turn(
            [], user_client=object(), user=SimpleNamespace(id="owner"),
            agent_id="agent-1", max_tool_rounds=99,
        )


def test_tool_output_is_bounded():
    assert len(orchestrator._bounded_json({"data": "x" * 20000})) <= orchestrator.MAX_TOOL_OUTPUT_CHARS


def test_tool_call_json_must_be_an_object(monkeypatch):
    client = FakeClient([
        FakeCompletion(_message(tool_calls=[_call("web_search", '["not","object"]')])),
        FakeCompletion(_message("Je ne peux pas traiter cet appel.")),
    ])
    _setup(monkeypatch, client)
    calls = []
    monkeypatch.setattr(orchestrator, "_execute_tool",
                        lambda *a, **k: calls.append("called"))
    result = orchestrator.run_agent_turn(
        [], user_client=object(), user=SimpleNamespace(id="owner"), agent_id="agent-1"
    )
    assert result == "Je ne peux pas traiter cet appel."
    assert calls == []


def test_tool_definitions_expose_only_owner_enabled_tools():
    names = {
        item["function"]["name"]
        for item in orchestrator._tool_definitions(["memory_read"])
    }
    assert names == {"memory_read"}


def test_dispatch_rejects_a_tool_not_enabled_for_this_agent():
    with pytest.raises(orchestrator.AgentOrchestrationError):
        orchestrator._execute_tool(
            "web_search", {"query": "test"},
            user_client=object(), user=SimpleNamespace(id="owner"),
            agent_id="agent-1", workspace_id="personal",
            request_id="00000000-0000-0000-0000-000000000001",
            enabled_tools=["memory_read"],
        )

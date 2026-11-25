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



def test_agent_chat_does_not_bypass_the_authorized_memory_read_tool():
    from pathlib import Path

    source = Path("agent_studio_ui.py").read_text(encoding="utf-8")
    assert "load_agent_memory_context" not in source
    assert "run_agent_turn(" in source


def test_agent_conversation_ui_persists_user_and_assistant_turn(monkeypatch):
    import sys
    import types
    import agent_studio_ui

    class Surface:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False

    class RerunSignal(BaseException):
        pass

    class FakeStreamlit:
        def __init__(self):
            self.session_state = {"sowia_language": "Français"}
            self.events = []
        def divider(self): pass
        def markdown(self, *args, **kwargs): pass
        def caption(self, *args, **kwargs): pass
        def button(self, *args, **kwargs): return False
        def selectbox(self, label, options, **kwargs): return options[0]
        def chat_message(self, role): return Surface()
        def write(self, *args, **kwargs): pass
        def chat_input(self, *args, **kwargs): return "  Reprendre le projet  "
        def spinner(self, *args, **kwargs): return Surface()
        def rerun(self): raise RerunSignal("STREAMLIT_RERUN")

    fake_st = FakeStreamlit()
    monkeypatch.setattr(agent_studio_ui, "st", fake_st)
    events = []
    conversation_id = "22222222-2222-4222-8222-222222222222"
    agent_id = "11111111-1111-4111-8111-111111111111"

    message_reads = {"count": 0}
    def list_messages(*args, **kwargs):
        message_reads["count"] += 1
        history = [{"role": "user", "content": "Ancien message"}]
        if message_reads["count"] > 1:
            history.append({"role": "user", "content": "Reprendre le projet"})
        return history

    store = types.SimpleNamespace(
        create_agent_conversation=lambda *a, **k: None,
        list_agent_conversations=lambda *a, **k: [{
            "id": conversation_id, "title": "Fil de travail",
        }],
        list_agent_messages=list_messages,
        save_agent_message=lambda *a, **k: events.append(("save", a[4], a[5])),
    )
    def run_turn(messages, **kwargs):
        events.append(("run", messages, kwargs))
        return "Réponse durable"
    monkeypatch.setitem(sys.modules, "agent_conversation_store", store)
    monkeypatch.setitem(sys.modules, "agent_orchestrator", types.SimpleNamespace(
        run_agent_turn=run_turn,
    ))

    try:
        agent_studio_ui._render_agent_conversation(
            object(), types.SimpleNamespace(id="owner-1"),
            {"id": agent_id, "name": "Agent test"}, "personal",
        )
    except RerunSignal as exc:
        assert str(exc) == "STREAMLIT_RERUN"
    else:
        pytest.fail("The UI should rerun after persisting the assistant response.")

    assert events[0] == ("save", "user", "Reprendre le projet")
    assert events[1][0] == "run"
    assert events[1][1][-1] == {"role": "user", "content": "Reprendre le projet"}
    assert events[1][2]["agent_id"] == agent_id
    assert events[1][2]["workspace_id"] == "personal"
    assert events[1][2]["language"] == "Français"
    assert events[2] == ("save", "assistant", "Réponse durable")

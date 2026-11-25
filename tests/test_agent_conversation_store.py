"""Tests for durable, owner-scoped SOW IA agent conversations."""
from types import SimpleNamespace
import uuid

import pytest

from agent_conversation_store import (
    create_agent_conversation,
    list_agent_conversations,
    list_agent_messages,
    save_agent_message,
)


class Query:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.filters = []
        self.payload = None
        self.updated = None
        self.sort = None
        self.limit_value = None

    def select(self, fields):
        return self

    def eq(self, key, value):
        self.filters.append((key, value))
        return self

    def order(self, key, desc=False):
        self.sort = (key, desc)
        return self

    def limit(self, value):
        self.limit_value = value
        return self

    def insert(self, payload):
        self.payload = payload
        return self

    def update(self, payload):
        self.updated = payload
        return self

    def execute(self):
        return SimpleNamespace(data=self.rows)


class Client:
    def __init__(self, rows_by_table):
        self.rows_by_table = rows_by_table
        self.queries = {}

    def table(self, name):
        query = Query(self.rows_by_table.get(name, []))
        self.queries.setdefault(name, []).append(query)
        return query


def test_create_agent_conversation_scopes_owner_agent_and_workspace():
    conversation_id = str(uuid.uuid4())
    client = Client({
        "sowia_agents": [{"id": "agent-id"}],
        "sowia_agent_conversations": [{
            "id": conversation_id, "title": "Nouvelle conversation",
        }],
    })

    result = create_agent_conversation(
        client, SimpleNamespace(id="owner-id"), "agent-id",
        workspace_id="personal",
    )

    assert result["id"] == conversation_id
    assert client.queries["sowia_agents"][0].filters == [
        ("id", "agent-id"), ("user_id", "owner-id"),
        ("workspace_id", "personal"), ("status", "active"),
    ]
    assert client.queries["sowia_agent_conversations"][0].payload == {
        "user_id": "owner-id",
        "agent_id": "agent-id",
        "workspace_id": "personal",
        "title": "Nouvelle conversation",
    }


def test_create_agent_conversation_rejects_non_active_or_unowned_agent():
    client = Client({"sowia_agents": []})
    with pytest.raises(PermissionError):
        create_agent_conversation(
            client, SimpleNamespace(id="owner-id"), str(uuid.uuid4())
        )


def test_list_agent_conversations_filters_owner_agent_and_workspace():
    client = Client({"sowia_agent_conversations": [{"id": str(uuid.uuid4())}]})
    user = SimpleNamespace(id="owner-id")
    agent_id = str(uuid.uuid4())

    rows = list_agent_conversations(
        client, user, agent_id, workspace_id="professional", limit=500
    )

    query = client.queries["sowia_agent_conversations"][0]
    assert len(rows) == 1
    assert ("user_id", "owner-id") in query.filters
    assert ("agent_id", agent_id) in query.filters
    assert ("workspace_id", "professional") in query.filters
    assert query.limit_value == 100


def test_list_agent_messages_returns_oldest_first_after_bounded_query():
    conversation_id = str(uuid.uuid4())
    client = Client({"sowia_agent_messages": [
        {"role": "assistant", "content": "second"},
        {"role": "user", "content": "first"},
    ]})

    rows = list_agent_messages(
        client, SimpleNamespace(id="owner-id"), str(uuid.uuid4()),
        conversation_id,
    )

    assert [row["content"] for row in rows] == ["first", "second"]
    assert client.queries["sowia_agent_messages"][0].sort == ("id", True)


def test_save_agent_message_checks_owner_and_conversation_before_insert():
    agent_id = str(uuid.uuid4())
    conversation_id = str(uuid.uuid4())
    client = Client({
        "sowia_agents": [{"id": agent_id}],
        "sowia_agent_conversations": [
            {"id": conversation_id, "title": "Nouvelle conversation"},
        ],
        "sowia_agent_messages": [{"id": 7}],
    })

    result = save_agent_message(
        client, SimpleNamespace(id="owner-id"), agent_id,
        conversation_id, "user", "Reprendre le projet",
    )

    inserted = client.queries["sowia_agent_messages"][0].payload
    assert result["id"] == 7
    assert inserted["user_id"] == "owner-id"
    assert inserted["agent_id"] == agent_id
    assert inserted["conversation_id"] == conversation_id
    assert inserted["role"] == "user"
    assert inserted["content"] == "Reprendre le projet"
    assert client.queries["sowia_agent_conversations"][-1].updated["title"] == "Reprendre le projet"


@pytest.mark.parametrize("role", ["system", "tool", "developer", ""])
def test_save_agent_message_rejects_non_chat_roles(role):
    client = Client({})
    with pytest.raises(ValueError):
        save_agent_message(
            client, SimpleNamespace(id="owner-id"), str(uuid.uuid4()),
            str(uuid.uuid4()), role, "Message",
        )


def test_save_agent_message_rejects_oversized_content_before_database_write():
    client = Client({})
    with pytest.raises(ValueError):
        save_agent_message(
            client, SimpleNamespace(id="owner-id"), str(uuid.uuid4()),
            str(uuid.uuid4()), "user", "x" * 12001,
        )
    assert client.queries == {}


def test_agent_conversation_requires_authenticated_owner():
    with pytest.raises(PermissionError):
        list_agent_conversations(
            Client({}), SimpleNamespace(id=""), str(uuid.uuid4())
        )

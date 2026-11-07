"""Tests for cloud-storage ownership guards and workspace-scoped queries."""
from types import SimpleNamespace

import pytest
import cloud_storage


class User:
    id = "user-123"


class FakeQuery:
    def __init__(self):
        self.filters = []
        self.inserted = None
        self.operations = []

    def select(self, columns):
        self.operations.append(("select", columns))
        return self

    def insert(self, payload):
        self.inserted = payload
        self.operations.append(("insert", payload))
        return self

    def delete(self):
        self.operations.append(("delete",))
        return self

    def eq(self, field, value):
        self.filters.append((field, value))
        return self

    def order(self, field, desc=False):
        self.operations.append(("order", field, desc))
        return self

    def limit(self, value):
        self.operations.append(("limit", value))
        return self

    def execute(self):
        return SimpleNamespace(data=[{"ok": True}])


class FakeClient:
    def __init__(self):
        self.tables = {}

    def table(self, name):
        return self.tables.setdefault(name, FakeQuery())


def test_storage_requires_authenticated_user():
    with pytest.raises(PermissionError, match="Connexion requise"):
        cloud_storage._user_id(None)


def test_storage_uses_authenticated_subject_id():
    assert cloud_storage._user_id(User()) == "user-123"


def test_workspace_is_validated():
    assert cloud_storage._workspace_id("professional") == "professional"
    with pytest.raises(ValueError, match="Espace de travail invalide"):
        cloud_storage._workspace_id("shared")


def test_memory_input_is_validated_before_database_write():
    class Client:
        def table(self, _name):
            raise AssertionError("Database must not be called for invalid input")

    with pytest.raises(ValueError):
        cloud_storage.add_memory(Client(), User(), "   ")
    with pytest.raises(ValueError):
        cloud_storage.add_memory(Client(), User(), "x" * 1001)


@pytest.mark.parametrize("workspace", ["personal", "professional"])
def test_list_memories_is_scoped_to_user_and_workspace(workspace):
    client = FakeClient()
    cloud_storage.list_memories(client, User(), workspace)
    filters = client.tables["sowia_memory_items"].filters
    assert ("user_id", "user-123") in filters
    assert ("workspace_id", workspace) in filters


def test_add_memory_writes_authenticated_user_and_workspace():
    client = FakeClient()
    cloud_storage.add_memory(client, User(), "Ma note", "professional")
    assert client.tables["sowia_memory_items"].inserted == {
        "user_id": "user-123",
        "workspace_id": "professional",
        "content": "Ma note",
    }


def test_delete_memory_is_scoped_to_memory_user_and_workspace():
    client = FakeClient()
    cloud_storage.delete_memory(client, User(), 42, "professional")
    filters = client.tables["sowia_memory_items"].filters
    assert ("id", 42) in filters
    assert ("user_id", "user-123") in filters
    assert ("workspace_id", "professional") in filters


def test_get_history_is_scoped_to_user_conversation_and_workspace():
    client = FakeClient()
    cloud_storage.get_history(client, User(), "private-session", workspace_id="professional")
    filters = client.tables["sowia_messages"].filters
    assert ("user_id", "user-123") in filters
    assert ("session_id", "private-session") in filters
    assert ("workspace_id", "professional") in filters


def test_clear_history_is_scoped_to_user_conversation_and_workspace():
    client = FakeClient()
    cloud_storage.clear_history(client, User(), "private-session", "professional")
    filters = client.tables["sowia_messages"].filters
    assert ("user_id", "user-123") in filters
    assert ("session_id", "private-session") in filters
    assert ("workspace_id", "professional") in filters


def test_save_message_writes_authenticated_user_conversation_and_workspace():
    client = FakeClient()
    cloud_storage.save_message(client, User(), "private-session", "user", "Bonjour", "professional")
    inserted = client.tables["sowia_messages"].inserted
    assert inserted["user_id"] == "user-123"
    assert inserted["workspace_id"] == "professional"
    assert inserted["session_id"] == "private-session"
    assert inserted["role"] == "user"
    assert inserted["content"] == "Bonjour"
    assert inserted["created_at"]


def test_save_message_rejects_unknown_role_before_database_write():
    class Client:
        def table(self, _name):
            raise AssertionError("Database must not be called for invalid role")

    with pytest.raises(ValueError, match="Rôle de message invalide"):
        cloud_storage.save_message(Client(), User(), "private-session", "admin", "Nope")

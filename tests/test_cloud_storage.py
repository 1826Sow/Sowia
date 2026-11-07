"""Tests for user- and workspace-scoped Supabase operations."""
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
        return self

    def delete(self):
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


def test_invalid_workspace_is_rejected():
    with pytest.raises(ValueError, match="Espace de travail invalide"):
        cloud_storage.list_memories(FakeClient(), User(), "shared")


@pytest.mark.parametrize("workspace", ["personal", "professional"])
def test_memory_queries_are_scoped_to_user_and_workspace(workspace):
    client = FakeClient()
    cloud_storage.list_memories(client, User(), workspace)
    filters = client.tables["sowia_memory_items"].filters
    assert ("user_id", "user-123") in filters
    assert ("workspace_id", workspace) in filters


@pytest.mark.parametrize("workspace", ["personal", "professional"])
def test_add_memory_writes_user_and_workspace(workspace):
    client = FakeClient()
    cloud_storage.add_memory(client, User(), "Ma note", workspace)
    assert client.tables["sowia_memory_items"].inserted == {
        "user_id": "user-123",
        "workspace_id": workspace,
        "content": "Ma note",
    }


def test_memory_input_is_validated_before_database_write():
    class Client:
        def table(self, _name):
            raise AssertionError("Database must not be called for invalid input")

    with pytest.raises(ValueError):
        cloud_storage.add_memory(Client(), User(), "   ")
    with pytest.raises(ValueError):
        cloud_storage.add_memory(Client(), User(), "x" * 1001)


def test_delete_memory_is_scoped_to_user_memory_and_workspace():
    client = FakeClient()
    cloud_storage.delete_memory(client, User(), 42, "professional")
    filters = client.tables["sowia_memory_items"].filters
    assert ("id", 42) in filters
    assert ("user_id", "user-123") in filters
    assert ("workspace_id", "professional") in filters


def test_history_is_scoped_to_user_session_and_workspace():
    client = FakeClient()
    cloud_storage.get_history(client, User(), "private-session", workspace_id="professional")
    filters = client.tables["sowia_messages"].filters
    assert ("user_id", "user-123") in filters
    assert ("session_id", "private-session") in filters
    assert ("workspace_id", "professional") in filters


def test_clear_history_is_scoped_to_user_session_and_workspace():
    client = FakeClient()
    cloud_storage.clear_history(client, User(), "private-session", "professional")
    filters = client.tables["sowia_messages"].filters
    assert ("user_id", "user-123") in filters
    assert ("session_id", "private-session") in filters
    assert ("workspace_id", "professional") in filters


@pytest.mark.parametrize("workspace", ["personal", "professional"])
def test_save_message_writes_user_session_and_workspace(workspace):
    client = FakeClient()
    cloud_storage.save_message(client, User(), "private-session", "user", "Bonjour", workspace)
    assert client.tables["sowia_messages"].inserted == {
        "user_id": "user-123",
        "workspace_id": workspace,
        "session_id": "private-session",
        "role": "user",
        "content": "Bonjour",
        "created_at": client.tables["sowia_messages"].inserted["created_at"],
    }


def test_save_message_rejects_unknown_role_before_database_write():
    class Client:
        def table(self, _name):
            raise AssertionError("Database must not be called for invalid role")

    with pytest.raises(ValueError, match="Rôle de message invalide"):
        cloud_storage.save_message(Client(), User(), "private-session", "admin", "Nope")

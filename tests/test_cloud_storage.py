"""Tests for cloud-storage ownership guards and user-scoped queries."""
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


def test_memory_input_is_validated_before_database_write():
    class Client:
        def table(self, _name):
            raise AssertionError("Database must not be called for invalid input")

    with pytest.raises(ValueError):
        cloud_storage.add_memory(Client(), User(), "   ")
    with pytest.raises(ValueError):
        cloud_storage.add_memory(Client(), User(), "x" * 1001)


def test_list_memories_is_scoped_to_authenticated_user():
    client = FakeClient()
    cloud_storage.list_memories(client, User())
    assert ("user_id", "user-123") in client.tables["sowia_memory_items"].filters


def test_add_memory_writes_authenticated_user_id():
    client = FakeClient()
    cloud_storage.add_memory(client, User(), "Ma note")
    assert client.tables["sowia_memory_items"].inserted == {
        "user_id": "user-123",
        "content": "Ma note",
    }


def test_delete_memory_is_scoped_to_memory_and_authenticated_user():
    client = FakeClient()
    cloud_storage.delete_memory(client, User(), 42)
    assert ("id", 42) in client.tables["sowia_memory_items"].filters
    assert ("user_id", "user-123") in client.tables["sowia_memory_items"].filters


def test_get_history_is_scoped_to_user_and_conversation():
    client = FakeClient()
    cloud_storage.get_history(client, User(), "private-session")
    filters = client.tables["sowia_messages"].filters
    assert ("user_id", "user-123") in filters
    assert ("session_id", "private-session") in filters


def test_clear_history_is_scoped_to_user_and_conversation():
    client = FakeClient()
    cloud_storage.clear_history(client, User(), "private-session")
    filters = client.tables["sowia_messages"].filters
    assert ("user_id", "user-123") in filters
    assert ("session_id", "private-session") in filters


def test_save_message_writes_authenticated_user_and_conversation():
    client = FakeClient()
    cloud_storage.save_message(client, User(), "private-session", "user", "Bonjour")
    assert client.tables["sowia_messages"].inserted == {
        "user_id": "user-123",
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

@pytest.mark.parametrize(
    "operation",
    [
        lambda client: cloud_storage.list_memories(client, None),
        lambda client: cloud_storage.add_memory(client, None, "note"),
        lambda client: cloud_storage.delete_memory(client, None, "memory-1"),
        lambda client: cloud_storage.get_history(client, None, "session-1"),
        lambda client: cloud_storage.clear_history(client, None, "session-1"),
        lambda client: cloud_storage.save_message(client, None, "session-1", "user", "hi"),
    ],
)
def test_every_memory_and_history_operation_rejects_anonymous_user_before_query(operation):
    client = FakeClient()
    with pytest.raises(PermissionError, match="Connexion requise"):
        operation(client)
    assert client.tables == {}


def test_history_query_caps_requested_limit_at_one_hundred():
    client = FakeClient()
    cloud_storage.get_history(client, User(), "private-session", limit=500)
    assert ("limit", 100) in client.tables["sowia_messages"].operations

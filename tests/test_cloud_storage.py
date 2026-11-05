"""Tests for cloud-storage ownership guards and per-user isolation."""
import pytest
import cloud_storage


class User:
    id = "user-123"


class FakeResponse:
    def __init__(self, data=None):
        self.data = data or []


class FakeQuery:
    def __init__(self, table_name, data=None):
        self.table_name = table_name
        self.data = data or []
        self.filters = []
        self.operations = []

    def select(self, fields):
        self.operations.append(("select", fields))
        return self

    def eq(self, field, value):
        self.filters.append((field, value))
        return self

    def order(self, *args, **kwargs):
        self.operations.append(("order", args, kwargs))
        return self

    def limit(self, value):
        self.operations.append(("limit", value))
        return self

    def insert(self, payload):
        self.operations.append(("insert", payload))
        return self

    def delete(self):
        self.operations.append(("delete",))
        return self

    def execute(self):
        return FakeResponse(self.data)


class FakeClient:
    def __init__(self, table_name, data=None):
        self.query = FakeQuery(table_name, data)

    def table(self, name):
        assert name == self.query.table_name
        return self.query


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


def test_list_memories_filters_by_authenticated_user():
    client = FakeClient("sowia_memory_items", [{"id": 1, "content": "privé"}])
    result = cloud_storage.list_memories(client, User())
    assert result[0]["content"] == "privé"
    assert ("user_id", "user-123") in client.query.filters


def test_add_memory_checks_duplicates_within_authenticated_user():
    client = FakeClient("sowia_memory_items", [])
    cloud_storage.add_memory(client, User(), "Une note privée")
    assert ("user_id", "user-123") in client.query.filters
    insertions = [op[1] for op in client.query.operations if op[0] == "insert"]
    assert insertions == [{"user_id": "user-123", "content": "Une note privée"}]


def test_delete_memory_filters_by_authenticated_user():
    client = FakeClient("sowia_memory_items")
    cloud_storage.delete_memory(client, User(), 42)
    assert ("id", 42) in client.query.filters
    assert ("user_id", "user-123") in client.query.filters
    assert ("delete",) in client.query.operations


def test_get_history_filters_by_user_and_session():
    client = FakeClient("sowia_messages", [
        {"role": "user", "content": "Bonjour"},
        {"role": "assistant", "content": "Bonjour !"},
    ])
    result = cloud_storage.get_history(client, User(), "session-abc", limit=20)
    assert len(result) == 2
    assert ("user_id", "user-123") in client.query.filters
    assert ("session_id", "session-abc") in client.query.filters


def test_clear_history_filters_by_user_and_session():
    client = FakeClient("sowia_messages")
    cloud_storage.clear_history(client, User(), "session-abc")
    assert ("user_id", "user-123") in client.query.filters
    assert ("session_id", "session-abc") in client.query.filters
    assert ("delete",) in client.query.operations


def test_save_message_attaches_authenticated_user_id():
    client = FakeClient("sowia_messages")
    cloud_storage.save_message(client, User(), "session-abc", "user", "Bonjour")
    insertions = [op[1] for op in client.query.operations if op[0] == "insert"]
    assert len(insertions) == 1
    assert insertions[0]["user_id"] == "user-123"
    assert insertions[0]["session_id"] == "session-abc"

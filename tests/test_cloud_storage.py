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

    def update(self, payload):
        self.inserted = payload
        self.operations.append(("update", payload))
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


@pytest.mark.parametrize(
    ("requested_limit", "expected_limit"),
    [(0, 1), (-5, 1), (1, 1), (30, 30), (100, 100), (500, 100), ("7", 7)],
)
def test_history_limit_is_clamped_to_safe_range(requested_limit, expected_limit):
    client = FakeClient()

    cloud_storage.get_history(
        client, User(), "private-session", limit=requested_limit, workspace_id="personal"
    )

    query = client.tables["sowia_messages"]
    assert ("limit", expected_limit) in query.operations
    assert ("order", "id", True) in query.operations


def test_history_query_keeps_requested_user_session_and_workspace_together():
    client = FakeClient()

    cloud_storage.get_history(
        client, User(), "professional-session", workspace_id="professional"
    )

    filters = client.tables["sowia_messages"].filters
    assert filters == [
        ("user_id", "user-123"),
        ("workspace_id", "professional"),
        ("session_id", "professional-session"),
    ]


def test_add_growth_lead_writes_user_workspace_and_validated_fields():
    client = FakeClient()
    cloud_storage.add_growth_lead(
        client, User(), "Startup Example", "États-Unis", "Amérique du Nord",
        "Accélérateur", "https://example.com", "https://example.com/partners",
        "À examiner", "professional",
    )
    payload = client.tables["sowia_growth_leads"].inserted
    assert payload["user_id"] == "user-123"
    assert payload["workspace_id"] == "professional"
    assert payload["organization"] == "Startup Example"
    assert payload["country"] == "États-Unis"
    assert payload["status"] == "À vérifier"


@pytest.mark.parametrize("website", ["javascript:alert(1)", "file:///etc/passwd", "not a url"])
def test_add_growth_lead_rejects_unsafe_urls_before_database_write(website):
    class Client:
        def table(self, _name):
            raise AssertionError("Database must not be called for invalid input")

    with pytest.raises(ValueError, match="HTTP"):
        cloud_storage.add_growth_lead(
            Client(), User(), "Startup", "France", "Europe", "SaaS", website
        )


def test_add_growth_lead_requires_organization_and_country():
    class Client:
        def table(self, _name):
            raise AssertionError("Database must not be called for invalid input")

    with pytest.raises(ValueError):
        cloud_storage.add_growth_lead(
            Client(), User(), " ", "France", "Europe", "SaaS", "https://example.com"
        )
    with pytest.raises(ValueError):
        cloud_storage.add_growth_lead(
            Client(), User(), "Startup", " ", "Europe", "SaaS", "https://example.com"
        )


def test_list_growth_leads_is_scoped_to_user_and_workspace():
    client = FakeClient()
    cloud_storage.list_growth_leads(client, User(), "professional")
    filters = client.tables["sowia_growth_leads"].filters
    assert ("user_id", "user-123") in filters
    assert ("workspace_id", "professional") in filters


def test_update_growth_lead_is_scoped_and_rejects_unknown_status():
    client = FakeClient()
    cloud_storage.update_growth_lead(
        client, User(), 7, "Contacté", "Premier échange", "personal"
    )
    query = client.tables["sowia_growth_leads"]
    assert query.inserted["status"] == "Contacté"
    assert ("id", 7) in query.filters
    assert ("user_id", "user-123") in query.filters
    assert ("workspace_id", "personal") in query.filters

    class Client:
        def table(self, _name):
            raise AssertionError("Database must not be called for invalid status")

    with pytest.raises(ValueError, match="Statut"):
        cloud_storage.update_growth_lead(
            Client(), User(), 7, "Envoyer tout", "", "personal"
        )


def test_delete_growth_lead_is_scoped_to_owner_and_workspace():
    client = FakeClient()
    cloud_storage.delete_growth_lead(client, User(), 9, "professional")
    filters = client.tables["sowia_growth_leads"].filters
    assert ("id", 9) in filters
    assert ("user_id", "user-123") in filters
    assert ("workspace_id", "professional") in filters



def test_accessibility_preferences_default_to_safe_values():
    class EmptyPreferenceQuery(FakeQuery):
        def execute(self):
            return SimpleNamespace(data=[])

    class Client:
        def table(self, name):
            assert name == "sowia_user_preferences"
            return EmptyPreferenceQuery()

    assert cloud_storage.get_accessibility_preferences(Client(), User()) == {
        "voice_readout": False,
        "large_text": False,
        "high_contrast": False,
        "privacy_screen": False,
    }


def test_accessibility_preferences_are_validated_and_saved_without_losing_language():
    class PreferenceQuery(FakeQuery):
        def execute(self):
            if self.inserted is None:
                return SimpleNamespace(data=[{"language": "English"}])
            return SimpleNamespace(data=[self.inserted])

        def upsert(self, payload, on_conflict=None):
            self.inserted = payload
            self.operations.append(("upsert", on_conflict))
            return self

    class Client:
        def __init__(self):
            self.query = PreferenceQuery()

        def table(self, name):
            assert name == "sowia_user_preferences"
            return self.query

    client = Client()
    saved = cloud_storage.set_accessibility_preferences(
        client, User(),
        {"voice_readout": True, "large_text": True, "high_contrast": False, "privacy_screen": True},
    )
    payload = saved[0]
    assert payload["language"] == "English"
    assert payload["user_id"] == "user-123"
    assert payload["accessibility"] == {
        "voice_readout": True, "large_text": True, "high_contrast": False, "privacy_screen": True
    }


@pytest.mark.parametrize(
    "invalid",
    [
        {"voice_readout": "yes"},
        {"unknown_option": True},
        ["voice_readout"],
        None,
    ],
)
def test_invalid_accessibility_preferences_are_rejected_before_database_write(invalid):
    class Client:
        def table(self, _name):
            raise AssertionError("Database must not be called for invalid preferences")

    with pytest.raises(ValueError):
        cloud_storage.set_accessibility_preferences(Client(), User(), invalid)

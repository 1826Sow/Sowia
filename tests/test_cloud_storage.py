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

    def range(self, start, end):
        self.operations.append(("range", start, end))
        return self

    def execute(self):
        if ("select", "id") in self.operations:
            return SimpleNamespace(data=[{"id": 123}])
        return SimpleNamespace(data=[{"ok": True}])


class FakeClient:
    def __init__(self):
        self.tables = {}

    def table(self, name):
        return self.tables.setdefault(name, FakeQuery())


def test_create_conversation_is_scoped_to_owner_and_workspace():
    client = FakeClient()
    query = client.table("sowia_conversations")
    query.execute = lambda: SimpleNamespace(data=[{
        "session_id": "session-abc", "title": "Nouvelle conversation",
        "created_at": "now", "updated_at": "now",
    }])
    result = cloud_storage.create_conversation(
        client, User(), "professional", session_id="session-abc"
    )
    assert result["session_id"] == "session-abc"
    assert query.inserted["user_id"] == "user-123"
    assert query.inserted["workspace_id"] == "professional"
    assert query.inserted["session_id"] == "session-abc"


def test_list_conversations_is_scoped_to_user_and_workspace():
    client = FakeClient()
    cloud_storage.list_conversations(client, User(), "professional")
    query = client.tables["sowia_conversations"]
    assert ("user_id", "user-123") in query.filters
    assert ("workspace_id", "professional") in query.filters
    assert ("range", 0, 99) in query.operations


def test_conversation_creation_rejects_missing_user():
    class Client:
        def table(self, _name):
            raise AssertionError("Database must not be called without a user")
    with pytest.raises(PermissionError, match="Connexion requise"):
        cloud_storage.create_conversation(Client(), None)


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
    result = cloud_storage.save_message(client, User(), "private-session", "user", "Bonjour", workspace)
    assert result == [{"id": 123}]
    assert ("select", "id") in client.tables["sowia_messages"].operations
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



def test_save_message_rejects_unconfirmed_database_insert():
    class EmptyInsertQuery(FakeQuery):
        def execute(self):
            return SimpleNamespace(data=[])

    class Client:
        def table(self, _name):
            return EmptyInsertQuery()

    with pytest.raises(RuntimeError, match="n’a pas confirmé"):
        cloud_storage.save_message(Client(), User(), "private-session", "user", "Bonjour")


def test_ensure_conversation_registers_legacy_session_without_rewriting_messages():
    client = FakeClient()
    query = client.table("sowia_conversations")
    calls = {"count": 0}

    def execute():
        calls["count"] += 1
        if calls["count"] == 1:
            return SimpleNamespace(data=[])
        return SimpleNamespace(data=[{
            "session_id": "legacy-session",
            "title": "Conversation précédente",
            "created_at": "now",
            "updated_at": "now",
        }])

    query.execute = execute
    result = cloud_storage.ensure_conversation(
        client, User(), "legacy-session", "personal"
    )

    assert result["session_id"] == "legacy-session"
    assert query.inserted == {
        "user_id": "user-123",
        "workspace_id": "personal",
        "session_id": "legacy-session",
        "title": "Conversation précédente",
    }
    assert "sowia_messages" not in client.tables


def test_ensure_conversation_is_idempotent_for_an_already_registered_session():
    client = FakeClient()
    query = client.table("sowia_conversations")
    query.execute = lambda: SimpleNamespace(data=[{
        "session_id": "existing-session",
        "title": "Mon projet",
        "created_at": "then",
        "updated_at": "now",
    }])

    result = cloud_storage.ensure_conversation(
        client, User(), "existing-session", "professional"
    )

    assert result["title"] == "Mon projet"
    assert query.inserted is None
    assert ("user_id", "user-123") in query.filters
    assert ("workspace_id", "professional") in query.filters
    assert ("session_id", "existing-session") in query.filters


def test_touch_conversation_updates_only_the_matching_owner_workspace_and_session():
    client = FakeClient()
    cloud_storage.touch_conversation(
        client, User(), "session-1", "professional", title="Nouveau titre"
    )

    query = client.tables["sowia_conversations"]
    assert query.inserted["title"] == "Nouveau titre"
    assert ("user_id", "user-123") in query.filters
    assert ("workspace_id", "professional") in query.filters
    assert ("session_id", "session-1") in query.filters




def test_register_legacy_conversations_derives_titles_from_first_user_message(monkeypatch):
    client = FakeClient()
    source_rows = [
        {
            "session_id": "legacy-1",
            "first_user_message": "  Bonjour   SOW IA, aide-moi à organiser mon projet.  ",
            "message_count": 4,
        },
        {
            "session_id": "legacy-2",
            "first_user_message": None,
            "message_count": 2,
        },
    ]
    rpc_calls = []
    client.rpc = lambda name, params: (
        rpc_calls.append((name, params))
        or SimpleNamespace(execute=lambda: SimpleNamespace(data=source_rows))
    )
    registered = []
    monkeypatch.setattr(
        cloud_storage,
        "ensure_conversation",
        lambda client, user, session_id, workspace_id, title=None: (
            registered.append((session_id, workspace_id, title))
            or {"session_id": session_id, "title": title}
        ),
    )

    result = cloud_storage.register_legacy_conversations(
        client, User(), "personal", limit=10
    )

    assert rpc_calls == [(
        "sowia_list_legacy_conversations", {"p_workspace_id": "personal"}
    )]
    assert registered == [
        ("legacy-1", "personal", "Bonjour SOW IA, aide-moi à organiser mon projet."),
        ("legacy-2", "personal", "Conversation précédente"),
    ]
    assert result == [
        {"session_id": "legacy-1", "title": "Bonjour SOW IA, aide-moi à organiser mon projet."},
        {"session_id": "legacy-2", "title": "Conversation précédente"},
    ]



def test_conversation_option_label_includes_explicit_utc_activity_time():
    label = cloud_storage.conversation_option_label({
        "title": "  Mon   projet  ",
        "updated_at": "2026-11-17T10:30:00+00:00",
    })
    assert label == "Mon projet · 17/11 10:30 UTC"


def test_conversation_option_label_falls_back_safely_for_missing_or_invalid_date():
    assert cloud_storage.conversation_option_label({
        "title": "Ancienne conversation",
        "updated_at": None,
    }) == "Ancienne conversation"
    assert cloud_storage.conversation_option_label({
        "title": "Conversation sans date",
        "updated_at": "date-invalide",
    }) == "Conversation sans date"

@pytest.mark.parametrize("invalid_session_id", [None, "", "   ", "x" * 129])
def test_session_scoped_storage_rejects_invalid_session_id_before_database_access(invalid_session_id):
    class Client:
        def table(self, _name):
            raise AssertionError("Database must not be called for an invalid session ID")

    with pytest.raises(ValueError, match="Identifiant de conversation invalide"):
        cloud_storage.get_history(Client(), User(), invalid_session_id)
    with pytest.raises(ValueError, match="Identifiant de conversation invalide"):
        cloud_storage.clear_history(Client(), User(), invalid_session_id)
    with pytest.raises(ValueError, match="Identifiant de conversation invalide"):
        cloud_storage.save_message(Client(), User(), invalid_session_id, "user", "Bonjour")


def test_session_id_is_normalized_before_scoped_storage_access():
    client = FakeClient()
    cloud_storage.get_history(client, User(), "  session-abc  ")
    assert ("session_id", "session-abc") in client.tables["sowia_messages"].filters



def test_list_conversations_supports_incremental_history_windows_safely():
    client = FakeClient()
    cloud_storage.list_conversations(client, User(), "personal", limit=2500)
    query = client.tables["sowia_conversations"]
    assert ("range", 0, 999) in query.operations
    assert ("user_id", "user-123") in query.filters
    assert ("workspace_id", "personal") in query.filters


def test_memory_list_uses_pagination_without_a_100_note_cap():
    client = FakeClient()
    cloud_storage.list_memories(client, User(), "personal", limit=1000, offset=1000)
    query = client.tables["sowia_memory_items"]
    assert ("range", 1000, 1999) in query.operations
    assert ("archived_at", "is.null") in query.filters


def test_memory_insert_validates_category_importance_and_tags():
    client = FakeClient()
    cloud_storage.add_memory(
        client, User(), "Technical decision", category="technical",
        importance=5, tags=["SOW IA", "Supabase", "SOW IA"], source="project",
        project_id=12,
    )
    payload = client.tables["sowia_memory_items"].inserted
    assert payload["category"] == "technical"
    assert payload["importance"] == 5
    assert payload["tags"] == ["SOW IA", "Supabase"]
    assert payload["project_id"] == 12


def test_memory_search_uses_owner_scoped_rpc_and_excludes_current_session():
    client = FakeClient()
    cloud_storage.search_memory_context(
        client, User(), "SOW IA project memory", "professional",
        exclude_session_id="active-session", limit=60,
    )
    assert client.rpc_name == "sowia_search_memory_context"
    assert client.rpc_params == {
        "p_workspace_id": "professional",
        "p_query": "SOW IA project memory",
        "p_exclude_session_id": "active-session",
        "p_project_id": None,
        "p_match_count": 60,
    }

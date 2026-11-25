"""Security and retrieval tests for the developer/agent memory gateway."""
from types import SimpleNamespace

import pytest

import cloud_storage
from memory_access import load_developer_agent_memory


class Query:
    def __init__(self, rows):
        self.rows = rows
        self.filters = []

    def select(self, fields):
        return self

    def eq(self, key, value):
        self.filters.append((key, value))
        return self

    def is_(self, key, value):
        self.filters.append((key, value))
        return self

    def limit(self, count):
        return self

    def execute(self):
        return SimpleNamespace(data=self.rows)


class Client:
    def __init__(self, projects):
        self.projects = projects
        self.query = None

    def table(self, name):
        assert name == "sowia_projects"
        self.query = Query(self.projects)
        return self.query


def test_agent_gets_general_and_selected_project_memory_only(monkeypatch):
    records = [
        {"content": "Préférence générale : réponses structurées.", "project_id": None},
        {"content": "Projet alpha : API développeur.", "project_id": 12},
        {"content": "Projet beta : secrets privés.", "project_id": 13},
    ]
    monkeypatch.setattr(cloud_storage, "list_memories", lambda *args: records)
    client = Client([{"id": 12}])
    result = load_developer_agent_memory(
        client, SimpleNamespace(id="user-1"), "professional", 12, "API développeur"
    )
    assert result == ["Projet alpha : API développeur."]
    assert ("user_id", "user-1") in client.query.filters
    assert ("workspace_id", "professional") in client.query.filters


def test_developer_without_project_sees_only_general_memory(monkeypatch):
    records = [
        {"content": "Mémoire générale.", "project_id": None},
        {"content": "Mémoire projet.", "project_id": 12},
    ]
    monkeypatch.setattr(cloud_storage, "list_memories", lambda *args: records)
    result = load_developer_agent_memory(
        Client([]), SimpleNamespace(id="user-1"), query="mémoire"
    )
    assert result == ["Mémoire générale."]


def test_unknown_or_archived_project_is_denied(monkeypatch):
    monkeypatch.setattr(cloud_storage, "list_memories", lambda *args: [])
    with pytest.raises(PermissionError):
        load_developer_agent_memory(
            Client([]), SimpleNamespace(id="user-1"), project_id=12
        )


def test_missing_authenticated_user_is_denied():
    with pytest.raises(PermissionError):
        load_developer_agent_memory(Client([]), SimpleNamespace(id=None))


@pytest.mark.parametrize("workspace", ["public", "admin", "../personal"])
def test_unknown_workspace_is_rejected(workspace):
    with pytest.raises(ValueError):
        load_developer_agent_memory(
            Client([]), SimpleNamespace(id="user-1"), workspace_id=workspace
        )


def test_invalid_project_identifier_is_rejected():
    with pytest.raises(ValueError):
        load_developer_agent_memory(
            Client([]), SimpleNamespace(id="user-1"), project_id="not-an-id"
        )


def test_metadata_is_not_exposed_to_agent_prompt(monkeypatch):
    records = [{
        "content": "Le guide explique les permissions API.",
        "project_id": None,
        "title": "Architecture interne",
        "tags": ["confidentiel"],
    }]
    monkeypatch.setattr(cloud_storage, "list_memories", lambda *args: records)
    result = load_developer_agent_memory(
        Client([]), SimpleNamespace(id="user-1"), query="permissions API"
    )
    assert result == ["Le guide explique les permissions API."]
    assert "confidentiel" not in " ".join(result)

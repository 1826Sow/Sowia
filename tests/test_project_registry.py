"""Tests for the persistent SOW IA project register."""
import pytest

from project_registry import (
    PROJECT_STATUSES, archive_project, create_project, list_projects, update_project,
)


class User:
    id = "user-123"


class Response:
    def __init__(self, data=None):
        self.data = data or []


class Query:
    def __init__(self, table):
        self.table_name = table
        self.filters = []
        self.payload = None
        self.operations = []
    def select(self, fields): self.operations.append(("select", fields)); return self
    def eq(self, key, value): self.filters.append(("eq", key, value)); return self
    def is_(self, key, value): self.filters.append(("is", key, value)); return self
    def order(self, key, desc=False): self.operations.append(("order", key, desc)); return self
    def limit(self, value): self.operations.append(("limit", value)); return self
    def insert(self, payload): self.payload = payload; self.operations.append(("insert",)); return self
    def update(self, payload): self.payload = payload; self.operations.append(("update",)); return self
    def execute(self): return Response([self.payload] if self.payload else [])
class Client:
    def __init__(self): self.query = None
    def table(self, name):
        self.query = Query(name)
        return self.query


def test_create_project_is_scoped_to_owner_and_workspace():
    client = Client()
    result = create_project(client, User(), " Projet test ", workspace_id="professional")
    assert result[0]["user_id"] == "user-123"
    assert result[0]["workspace_id"] == "professional"
    assert result[0]["title"] == "Projet test"


def test_list_projects_filters_owner_workspace_and_archives():
    client = Client()
    list_projects(client, User(), workspace_id="personal")
    assert ("eq", "user_id", "user-123") in client.query.filters
    assert ("eq", "workspace_id", "personal") in client.query.filters
    assert ("is", "archived_at", "null") in client.query.filters


def test_update_rejects_invalid_status_and_unknown_fields():
    client = Client()
    with pytest.raises(ValueError):
        update_project(client, User(), 1, status="Inventé")
    with pytest.raises(ValueError):
        update_project(client, User(), 1, admin=True)
    assert PROJECT_STATUSES == {"En cours", "À tester", "Validé", "Terminé"}


def test_archive_is_soft_and_scoped():
    client = Client()
    archive_project(client, User(), 7, workspace_id="professional")
    assert ("eq", "user_id", "user-123") in client.query.filters
    assert ("eq", "workspace_id", "professional") in client.query.filters
    assert ("is", "archived_at", "null") in client.query.filters
    assert client.query.payload["archived_at"]


def test_invalid_workspace_and_missing_identity_are_rejected():
    client = Client()
    with pytest.raises(ValueError):
        list_projects(client, User(), workspace_id="admin")
    class Anonymous: id = None
    with pytest.raises(PermissionError):
        create_project(client, Anonymous(), "Test")

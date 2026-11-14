"""Tests for the persistent SOW IA project register."""
import pytest

from project_registry import (
    PROJECT_STATUSES, archive_project, create_project, list_projects, restore_project, update_project,
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
    assert result[0]["title"] == "Projet test"\n    assert ("select", "id, user_id, workspace_id, title, description, status, created_at, updated_at") in client.query.operations


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


def test_restore_project_is_scoped_and_clears_archive_timestamp():
    client = Client()
    restore_project(client, User(), 9, workspace_id="professional")
    assert ("eq", "id", 9) in client.query.filters
    assert ("eq", "user_id", "user-123") in client.query.filters
    assert ("eq", "workspace_id", "professional") in client.query.filters
    assert client.query.payload["archived_at"] is None
    assert client.query.payload["updated_at"]



@pytest.mark.parametrize("bad_url", [
    "http://example.com/file.pdf",
    "https://",
    "https:///missing-host",
    "https://user:pass@example.com/file.pdf",
    "https://example.com:invalid/file.pdf",
    "https://example.com/has space",
])
def test_deliverables_reject_unsafe_or_malformed_urls(bad_url):
    client = Client()
    with pytest.raises(ValueError):
        create_project(
            client, User(), "Projet avec lien",
            deliverables=[{"title": "Document", "url": bad_url}],
        )


def test_deliverables_accept_valid_https_and_optional_url():
    client = Client()
    result = create_project(
        client, User(), "Projet avec liens",
        deliverables=[
            {"title": "PDF", "url": "https://example.com/files/report.pdf"},
            {"title": "Document à ajouter", "url": ""},
        ],
    )
    assert len(result[0]["deliverables"]) == 2


def test_deliverables_validate_on_update_and_enforce_limit():
    client = Client()
    with pytest.raises(ValueError):
        update_project(
            client, User(), 1,
            deliverables=[{"title": "Lien non sécurisé", "url": "javascript:alert(1)"}],
        )
    with pytest.raises(ValueError):
        create_project(
            client, User(), "Trop de livrables",
            deliverables=[{"title": f"Fichier {index}", "url": ""} for index in range(101)],
        )


def test_create_project_rejects_empty_insert_representation():
    class EmptyQuery(Query):
        def execute(self):
            return Response([])

    class EmptyClient:
        def table(self, name):
            return EmptyQuery(name)

    with pytest.raises(RuntimeError, match="Supabase n’a confirmé aucune ligne créée"):
        create_project(EmptyClient(), User(), "Projet sans confirmation")

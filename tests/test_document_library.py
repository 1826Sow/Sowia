import pytest

import document_library


def test_search_match_returns_page_and_excerpt():
    text = "Introduction\n--- Page 1 ---\nContenu initial\n--- Page 2 ---\nLa recette est prête."
    result = document_library._search_match(text, "recette")
    assert result is not None
    assert result["page"] == 2
    assert "La recette est prête." in result["snippet"]


def test_search_match_ignores_case_and_accents():
    text = "--- Page 4 ---\nL'École prépare un résumé."
    result = document_library._search_match(text, "ecole")
    assert result is not None
    assert result["page"] == 4
    assert "École" in result["snippet"]


def test_search_match_returns_none_when_not_found():
    assert document_library._search_match("--- Page 1 ---\nBonjour", "introuvable") is None


def test_search_local_rejects_empty_query():
    with pytest.raises(ValueError):
        document_library.search_local("   ")


def test_search_local_finds_accented_text(tmp_path, monkeypatch):
    monkeypatch.setattr(document_library, "DB_PATH", tmp_path / "sowia_test.db")
    document_library.save_local(
        "Document test",
        "test.pdf",
        "--- Page 3 ---\nL'École prépare un résumé.",
    )
    results = document_library.search_local("ecole")
    assert len(results) == 1
    assert results[0]["page"] == 3
    assert "École" in results[0]["snippet"]


def test_search_match_keeps_correct_offset_after_accented_characters():
    text = "--- Page 1 ---\\nÉléments précédents\\n--- Page 2 ---\\nLe résumé final."
    result = document_library._search_match(text, "resume")
    assert result is not None
    assert result["page"] == 2
    assert "résumé final" in result["snippet"]



class _FakeResponse:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, data):
        self.data = data
        self.filters = []

    def select(self, *_args):
        return self

    def eq(self, field, value):
        self.filters.append((field, value))
        return self

    @property
    def not_(self):
        self._negated = True
        return self

    def is_(self, field, value):
        operator = "not_is" if self._negated else "is"
        self._negated = False
        self.filters.append((field, operator, value))
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, *_args):
        return self

    def execute(self):
        return _FakeResponse(self.data)


class _FakeClient:
    def __init__(self, data):
        self.query = _FakeQuery(data)

    def table(self, name):
        assert name == "sowia_documents"
        return self.query


def test_search_cloud_filters_to_authenticated_user():
    user = type("User", (), {"id": "user-123"})()
    client = _FakeClient([{
        "id": 7,
        "title": "Document privé",
        "filename": "prive.pdf",
        "extracted_text": "--- Page 2 ---\nMot confidentiel",
        "created_at": "2026-11-05T00:00:00Z",
    }])

    results = document_library.search_cloud(client, user, "confidentiel")

    assert [item["id"] for item in results] == [7]
    assert ("user_id", "user-123") in client.query.filters


def test_search_cloud_requires_authenticated_user():
    client = _FakeClient([])
    user = type("User", (), {"id": None})()

    with pytest.raises(PermissionError, match="Connexion requise"):
        document_library.search_cloud(client, user, "document")


class _CrudQuery:
    def __init__(self, data=None):
        self.data = data or []
        self.filters = []
        self.inserted = None
        self.deleted = False
        self.updated = None
        self._negated = False

    def insert(self, payload):
        self.inserted = payload
        return self

    def update(self, payload):
        self.updated = payload
        return self

    def select(self, *_args):
        return self

    def eq(self, field, value):
        self.filters.append((field, value))
        return self

    @property
    def not_(self):
        self._negated = True
        return self

    def is_(self, field, value):
        operator = "not_is" if self._negated else "is"
        self._negated = False
        self.filters.append((field, operator, value))
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, *_args):
        return self

    def delete(self):
        self.deleted = True
        return self

    def execute(self):
        return _FakeResponse(self.data)


class _CrudClient:
    def __init__(self, data=None):
        self.query = _CrudQuery(data)

    def table(self, name):
        assert name == "sowia_documents"
        return self.query


def test_save_cloud_attaches_authenticated_owner_and_validates_document():
    user = type("User", (), {"id": "owner-42"})()
    client = _CrudClient()
    document_library.save_cloud(client, user, "Mon PDF", "mon.pdf", "Texte extrait")

    assert client.query.inserted == {
        "user_id": "owner-42",
        "title": "Mon PDF",
        "filename": "mon.pdf",
        "extracted_text": "Texte extrait",
        "text_length": len("Texte extrait"),
    }


def test_save_cloud_rejects_missing_user_before_insert():
    user = type("User", (), {"id": None})()
    client = _CrudClient()

    with pytest.raises(PermissionError, match="Connexion requise"):
        document_library.save_cloud(client, user, "Mon PDF", "mon.pdf", "Texte extrait")

    assert client.query.inserted is None


def test_list_cloud_filters_by_authenticated_owner():
    user = type("User", (), {"id": "owner-42"})()
    client = _CrudClient([{"id": 9, "title": "Privé"}])

    result = document_library.list_cloud(client, user)

    assert result[0]["id"] == 9
    assert ("user_id", "owner-42") in client.query.filters


def test_get_cloud_filters_by_owner_and_document_id():
    user = type("User", (), {"id": "owner-42"})()
    client = _CrudClient([{"id": 9, "extracted_text": "privé"}])

    result = document_library.get_cloud(client, user, 9)

    assert result["id"] == 9
    assert ("user_id", "owner-42") in client.query.filters
    assert ("id", 9) in client.query.filters


def test_delete_cloud_filters_by_owner_and_document_id():
    user = type("User", (), {"id": "owner-42"})()
    client = _CrudClient()

    document_library.delete_cloud(client, user, 9)

    assert client.query.deleted is True
    assert ("user_id", "owner-42") in client.query.filters
    assert ("id", 9) in client.query.filters



@pytest.mark.parametrize(
    "operation",
    [
        lambda client, user: document_library.list_cloud(client, user),
        lambda client, user: document_library.get_cloud(client, user, 9),
        lambda client, user: document_library.delete_cloud(client, user, 9),
    ],
    ids=["list", "get", "delete"],
)
def test_cloud_document_reads_and_deletes_reject_missing_user(operation):
    user = type("User", (), {"id": None})()
    client = _CrudClient([{"id": 9, "title": "Document privé"}])

    with pytest.raises(PermissionError, match="Connexion requise"):
        operation(client, user)

    # No ownership filter or database query may be executed for an anonymous user.
    assert client.query.filters == []


@pytest.mark.parametrize("invalid_id", [None, "", "abc", "1.5", 0, -1, 1.5, True])
def test_document_id_rejects_invalid_values_before_database_access(invalid_id):
    with pytest.raises(ValueError, match="Identifiant de document invalide"):
        document_library._document_id(invalid_id)


@pytest.mark.parametrize(
    "operation",
    [
        lambda client, user, value: document_library.get_cloud(client, user, value),
        lambda client, user, value: document_library.delete_cloud(client, user, value),
    ],
    ids=["get", "delete"],
)
def test_cloud_document_operations_reject_invalid_ids_before_query(operation):
    user = type("User", (), {"id": "owner-42"})()
    client = _CrudClient([{"id": 9, "title": "Document privé"}])

    with pytest.raises(ValueError, match="Identifiant de document invalide"):
        operation(client, user, "not-an-id")

    assert client.query.filters == []
    assert client.query.deleted is False


def test_document_id_accepts_positive_integer_and_numeric_string():
    assert document_library._document_id(12) == 12
    assert document_library._document_id("12") == 12


@pytest.mark.parametrize(
    "untrusted_name",
    [
        "../../secret.pdf",
        "C:/Users/Public/document.pdf",
        "../../<script>alert(1)</script>.pdf",
        "",
        ".pdf",
        "nom avec espaces et accents éà.pdf",
    ],
)
def test_safe_text_download_name_never_contains_path_or_unsafe_characters(untrusted_name):
    result = document_library.safe_text_download_name(untrusted_name)
    assert result.startswith("sowia_")
    assert result.endswith(".txt")
    assert "/" not in result
    assert chr(92) not in result
    assert "<" not in result
    assert ">" not in result


def test_safe_text_download_name_has_fallback_for_empty_stem():
    assert document_library.safe_text_download_name(".pdf") == "sowia_document.txt"



def test_cloud_list_and_get_exclude_trashed_documents():
    user = type("User", (), {"id": "owner-42"})()
    client = _CrudClient([{"id": 9, "title": "Actif"}])

    document_library.list_cloud(client, user)
    assert ("user_id", "owner-42") in client.query.filters
    assert ("deleted_at", "is", "null") in client.query.filters

    client = _CrudClient([{"id": 9, "title": "Actif", "extracted_text": "Texte"}])
    document_library.get_cloud(client, user, 9)
    assert ("deleted_at", "is", "null") in client.query.filters


@pytest.mark.parametrize(
    "operation",
    [
        lambda client, user: document_library.update_cloud_category(client, user, 9, "Finances"),
        lambda client, user: document_library.update_cloud_folder(client, user, 9, "Archives"),
        lambda client, user: document_library.trash_cloud(client, user, 9),
    ],
    ids=["category", "folder", "trash"],
)
def test_cloud_mutations_are_owner_scoped_and_only_touch_active_documents(operation):
    user = type("User", (), {"id": "owner-42"})()
    client = _CrudClient()

    operation(client, user)

    assert ("user_id", "owner-42") in client.query.filters
    assert ("id", 9) in client.query.filters
    assert ("deleted_at", "is", "null") in client.query.filters


@pytest.mark.parametrize(
    "operation",
    [
        lambda client, user: document_library.update_cloud_category(client, user, 9, "Finances"),
        lambda client, user: document_library.update_cloud_folder(client, user, 9, "Archives"),
        lambda client, user: document_library.trash_cloud(client, user, 9),
    ],
    ids=["category", "folder", "trash"],
)
def test_cloud_mutations_reject_missing_user_before_query(operation):
    user = type("User", (), {"id": None})()
    client = _CrudClient()

    with pytest.raises(PermissionError, match="Connexion requise"):
        operation(client, user)

    assert client.query.filters == []



def test_cloud_trash_listing_is_scoped_and_only_returns_deleted_rows():
    user = type("User", (), {"id": "owner-42"})()
    client = _CrudClient([{"id": 9, "title": "Supprimé"}])

    result = document_library.list_trashed_cloud(client, user)

    assert result[0]["id"] == 9
    assert ("user_id", "owner-42") in client.query.filters
    assert ("deleted_at", "not_is", "null") in client.query.filters


def test_cloud_restore_only_clears_deleted_at_for_the_owner():
    user = type("User", (), {"id": "owner-42"})()
    client = _CrudClient()

    document_library.restore_cloud(client, user, 9)

    assert client.query.updated == {"deleted_at": None}
    assert ("user_id", "owner-42") in client.query.filters
    assert ("id", 9) in client.query.filters
    assert ("deleted_at", "not_is", "null") in client.query.filters


def test_cloud_permanent_delete_only_deletes_trashed_documents_for_the_owner():
    user = type("User", (), {"id": "owner-42"})()
    client = _CrudClient()

    document_library.permanently_delete_cloud(client, user, 9)

    assert client.query.deleted is True
    assert ("user_id", "owner-42") in client.query.filters
    assert ("id", 9) in client.query.filters
    assert ("deleted_at", "not_is", "null") in client.query.filters


@pytest.mark.parametrize(
    "operation",
    [
        lambda client, user: document_library.list_trashed_cloud(client, user),
        lambda client, user: document_library.restore_cloud(client, user, 9),
        lambda client, user: document_library.permanently_delete_cloud(client, user, 9),
    ],
    ids=["list-trash", "restore", "permanent-delete"],
)
def test_cloud_trash_operations_reject_missing_user_before_query(operation):
    user = type("User", (), {"id": None})()
    client = _CrudClient()

    with pytest.raises(PermissionError, match="Connexion requise"):
        operation(client, user)

    assert client.query.filters == []
    assert client.query.deleted is False
    assert client.query.updated is None

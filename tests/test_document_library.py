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

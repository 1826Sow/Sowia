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

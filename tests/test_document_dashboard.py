import pytest

from document_dashboard import summarize_library


def test_empty_library_returns_zeroed_metrics():
    result = summarize_library([])
    assert result["document_count"] == 0
    assert result["total_characters"] == 0
    assert result["average_characters"] == 0
    assert result["category_counts"] == {}
    assert result["folder_counts"] == {}
    assert result["recent_documents"] == []
    assert result["comparison_count"] == 0
    assert result["latest_document_at"] is None


def test_aggregates_categories_folders_and_character_counts():
    documents = [
        {"id": 1, "title": "Facture", "filename": "facture.pdf", "text_length": 120, "created_at": "2026-01-01"},
        {"id": 2, "title": "Cours", "filename": "cours.pdf", "text_length": 80, "category": "Études", "folder": "École", "created_at": "2026-02-01"},
        {"id": 3, "title": "Contrat", "filename": "contrat.pdf", "text_length": 0, "category": "Administratif", "folder": "Général"},
    ]
    result = summarize_library(documents, comparison_reports=[{}, {}])
    assert result["document_count"] == 3
    assert result["total_characters"] == 200
    assert result["average_characters"] == 67
    assert result["category_counts"] == {"Administratif": 1, "Finances": 1, "Études": 1}
    assert result["folder_counts"] == {"Général": 2, "École": 1}
    assert result["comparison_count"] == 2


def test_recent_documents_are_sorted_newest_first_and_limited():
    docs = [
        {"id": 1, "created_at": "2026-01-01"},
        {"id": 2, "created_at": "2026-03-01"},
        {"id": 3, "created_at": "2026-02-01"},
    ]
    result = summarize_library(docs, recent_limit=2)
    assert [item["id"] for item in result["recent_documents"]] == [2, 3]
    assert result["latest_document_at"] == "2026-03-01"


@pytest.mark.parametrize("limit", [0, -1, 21, True, "invalid"])
def test_rejects_invalid_recent_limit(limit):
    with pytest.raises(ValueError):
        summarize_library([], recent_limit=limit)


def test_invalid_text_lengths_are_treated_as_zero():
    result = summarize_library([{"text_length": "unknown"}])
    assert result["total_characters"] == 0

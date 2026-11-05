import io
import zipfile

import pytest

from document_export import build_documents_zip


def test_builds_zip_with_text_and_metadata():
    payload = build_documents_zip([{
        "title": "Facture mars",
        "filename": "facture-mars.pdf",
        "category": "Finances",
        "folder": "Comptabilité",
        "created_at": "2026-03-01",
        "extracted_text": "Total : 125 euros",
    }])
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        assert archive.namelist() == ["facture-mars.txt"]
        content = archive.read("facture-mars.txt").decode("utf-8")
    assert "Titre : Facture mars" in content
    assert "Catégorie : Finances" in content
    assert "Total : 125 euros" in content


def test_duplicate_names_are_made_unique():
    docs = [
        {"filename": "rapport.pdf", "extracted_text": "Premier"},
        {"filename": "rapport.docx", "extracted_text": "Deuxième"},
    ]
    with zipfile.ZipFile(io.BytesIO(build_documents_zip(docs))) as archive:
        assert archive.namelist() == ["rapport.txt", "rapport_2.txt"]


def test_rejects_empty_or_too_many_documents():
    with pytest.raises(ValueError):
        build_documents_zip([])
    with pytest.raises(ValueError):
        build_documents_zip([{"extracted_text": "x"}] * 21)


def test_skips_records_without_text():
    with pytest.raises(ValueError):
        build_documents_zip([{"filename": "vide.pdf", "extracted_text": "  "}])

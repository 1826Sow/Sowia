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


def test_rejects_single_document_over_size_limit():
    with pytest.raises(ValueError, match="100 000 caractères"):
        build_documents_zip([{"extracted_text": "x" * 100_001}])


def test_rejects_total_archive_over_size_limit():
    docs = [{"extracted_text": "x" * 100_000} for _ in range(16)]
    with pytest.raises(ValueError, match="taille totale"):
        build_documents_zip(docs, max_total_chars=1_500_000)


def test_metadata_newlines_cannot_inject_fake_entries():
    docs = [{
        "filename": "notes.txt",
        "title": "Titre\nFausse entrée : oui",
        "category": "Autres\r\nAdministrateur",
        "extracted_text": "Texte",
    }]
    with zipfile.ZipFile(io.BytesIO(build_documents_zip(docs))) as archive:
        content = archive.read("notes.txt").decode("utf-8")
    assert "Titre : Titre Fausse entrée : oui" in content
    assert "Catégorie : Autres Administrateur" in content


@pytest.mark.parametrize("limit", [0, -1, 21, True, "20"])
def test_rejects_invalid_document_limits(limit):
    with pytest.raises(ValueError):
        build_documents_zip([{"extracted_text": "x"}], max_documents=limit)


@pytest.mark.parametrize("limit", [0, -1, 2_000_001, True, "100"])
def test_rejects_invalid_total_size_limits(limit):
    with pytest.raises(ValueError):
        build_documents_zip([{"extracted_text": "x"}], max_total_chars=limit)



@pytest.mark.parametrize(
    "filename",
    [
        "../../secret.pdf",
        "C:\\Users\\Public\\document.pdf",
        "/etc/passwd",
        "../..\\private\\notes.pdf",
        "<script>alert(1)</script>.pdf",
    ],
)
def test_archive_names_never_contain_paths_or_unsafe_characters(filename):
    docs = [{"filename": filename, "extracted_text": "Texte privé"}]
    with zipfile.ZipFile(io.BytesIO(build_documents_zip(docs))) as archive:
        names = archive.namelist()

    assert len(names) == 1
    assert "/" not in names[0]
    assert chr(92) not in names[0]
    assert ".." not in names[0]
    assert names[0].endswith(".txt")


def test_archive_names_are_unique_even_when_case_differs():
    docs = [
        {"filename": "Report.pdf", "extracted_text": "Premier"},
        {"filename": "report.docx", "extracted_text": "Deuxième"},
    ]
    with zipfile.ZipFile(io.BytesIO(build_documents_zip(docs))) as archive:
        names = archive.namelist()

    assert names == ["Report.txt", "report_2.txt"]
    assert len({name.casefold() for name in names}) == len(names)

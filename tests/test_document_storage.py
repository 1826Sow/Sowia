"""Tests for private PDF storage ownership and workspace isolation."""
from io import BytesIO

import pytest
from pypdf import PdfWriter
import document_storage as docs


def valid_pdf(page_count=1, password=None):
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=72, height=72)
    if password:
        writer.encrypt(password)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


class User:
    id = "user-123"


class FakeBucket:
    def __init__(self):
        self.uploaded = None
        self.listed = []
        self.downloaded = None
        self.removed = None

    def upload(self, path, content, file_options=None):
        self.uploaded = (path, content, file_options)
        return {"path": path}

    def list(self, prefix):
        self.listed.append(prefix)
        return [{"name": "report.pdf"}]

    def download(self, path):
        self.downloaded = path
        return b"%PDF"

    def remove(self, paths):
        self.removed = paths
        return paths


class FakeClient:
    def __init__(self):
        self.bucket = FakeBucket()
        self.storage = self

    def from_(self, bucket_name):
        assert bucket_name == docs.BUCKET_NAME
        return self.bucket


@pytest.mark.parametrize("workspace", ["personal", "professional"])
def test_upload_is_stored_under_user_and_workspace_folder(workspace):
    client = FakeClient()
    payload = valid_pdf()
    path = docs.upload_document(client, User(), "Mon rapport.pdf", payload, workspace)
    assert path.startswith(f"user-123/{workspace}/")
    assert path.endswith("_Mon_rapport.pdf")
    assert client.bucket.uploaded[1] == payload
    assert client.bucket.uploaded[2]["content-type"] == "application/pdf"


def test_list_documents_queries_only_selected_workspace_and_returns_full_paths():
    client = FakeClient()
    documents = docs.list_documents(client, User(), "professional")
    assert client.bucket.listed == ["user-123/professional"]
    assert documents[0]["path"] == "user-123/professional/report.pdf"


def test_personal_listing_includes_legacy_flat_files_and_personal_folder():
    client = FakeClient()
    documents = docs.list_documents(client, User(), "personal")
    assert client.bucket.listed == ["user-123", "user-123/personal"]
    assert documents[0]["path"] == "user-123/report.pdf"
    assert documents[1]["path"] == "user-123/personal/report.pdf"


def test_download_rejects_another_users_path_before_storage_access():
    client = FakeClient()
    with pytest.raises(PermissionError):
        docs.download_document(client, User(), "other-user/personal/report.pdf", "personal")
    assert client.bucket.downloaded is None


def test_workspace_path_cannot_be_read_from_other_workspace():
    client = FakeClient()
    with pytest.raises(ValueError, match="Chemin de document invalide"):
        docs.download_document(client, User(), "user-123/professional/report.pdf", "personal")
    assert client.bucket.downloaded is None


def test_delete_rejects_path_traversal():
    client = FakeClient()
    with pytest.raises(ValueError):
        docs.delete_document(client, User(), "user-123/personal/../private.pdf", "personal")
    assert client.bucket.removed is None


def test_upload_rejects_non_pdf_and_oversized_files_before_storage_access():
    client = FakeClient()
    with pytest.raises(ValueError, match="PDF"):
        docs.upload_document(client, User(), "notes.txt", b"hello")
    with pytest.raises(ValueError, match="10 Mo"):
        docs.upload_document(client, User(), "large.pdf", b"x" * (docs.MAX_DOCUMENT_BYTES + 1))
    assert client.bucket.uploaded is None


def test_upload_rejects_pdf_extension_without_pdf_signature():
    client = FakeClient()
    with pytest.raises(ValueError, match="PDF valide"):
        docs.upload_document(client, User(), "fake.pdf", b"this is not a PDF")
    assert client.bucket.uploaded is None


def test_upload_sanitizes_path_and_special_characters_in_filename():
    client = FakeClient()
    path = docs.upload_document(client, User(), "../../rapport confidentiel.pdf", valid_pdf())
    assert path.startswith("user-123/personal/")
    assert path.endswith("_rapport_confidentiel.pdf")
    assert ".." not in path


def test_storage_requires_authenticated_user():
    with pytest.raises(PermissionError, match="Connexion requise"):
        docs.list_documents(FakeClient(), None)


def test_delete_rejects_another_users_path_before_storage_access():
    client = FakeClient()
    with pytest.raises(PermissionError):
        docs.delete_document(client, User(), "other-user/personal/report.pdf", "personal")
    assert client.bucket.removed is None


def test_workspace_path_cannot_be_deleted_from_other_workspace():
    client = FakeClient()
    with pytest.raises(ValueError, match="Chemin de document invalide"):
        docs.delete_document(client, User(), "user-123/professional/report.pdf", "personal")
    assert client.bucket.removed is None


def test_legacy_flat_file_cannot_be_deleted_from_professional_workspace():
    client = FakeClient()
    with pytest.raises(ValueError, match="Chemin de document invalide"):
        docs.delete_document(client, User(), "user-123/report.pdf", "professional")
    assert client.bucket.removed is None


def test_upload_rejects_missing_user_and_invalid_workspace_before_storage_access():
    client = FakeClient()
    with pytest.raises(PermissionError, match="Connexion requise"):
        docs.upload_document(client, None, "report.pdf", valid_pdf(), "personal")
    with pytest.raises(ValueError, match="Espace de travail invalide"):
        docs.upload_document(client, User(), "report.pdf", valid_pdf(), "shared")
    assert client.bucket.uploaded is None



def test_upload_rejects_malformed_pdf_with_a_pdf_header():
    client = FakeClient()
    with pytest.raises(ValueError, match="PDF valide ou lisible"):
        docs.upload_document(client, User(), "broken.pdf", b"%PDF-1.7\nnot a real PDF")
    assert client.bucket.uploaded is None


def test_upload_rejects_encrypted_pdf():
    client = FakeClient()
    with pytest.raises(ValueError, match="mot de passe"):
        docs.upload_document(client, User(), "encrypted.pdf", valid_pdf(password="secret"))
    assert client.bucket.uploaded is None


def test_upload_rejects_pdf_over_page_limit():
    client = FakeClient()
    payload = valid_pdf(docs.MAX_DOCUMENT_PAGES + 1)
    with pytest.raises(ValueError, match="500 pages"):
        docs.upload_document(client, User(), "too-many-pages.pdf", payload)
    assert client.bucket.uploaded is None


def test_upload_accepts_a_structurally_valid_pdf():
    client = FakeClient()
    payload = valid_pdf()
    path = docs.upload_document(client, User(), "valid.pdf", payload)
    assert path.startswith("user-123/personal/")
    assert client.bucket.uploaded[1] == payload


def test_display_document_name_hides_only_a_32_character_hex_prefix():
    assert docs.display_document_name("a" * 32 + "_rapport.pdf") == "rapport.pdf"
    assert docs.display_document_name("rapport_final.pdf") == "rapport_final.pdf"
    assert docs.display_document_name("badprefix_rapport.pdf") == "badprefix_rapport.pdf"


def test_filter_documents_searches_case_insensitively_by_display_name():
    documents = [
        {"name": "a" * 32 + "_Facture_2026.pdf", "path": "u/p/a"},
        {"name": "b" * 32 + "_Compte_Rendu.pdf", "path": "u/p/b"},
    ]
    result = docs.filter_documents(documents, query="facture")
    assert [item["path"] for item in result] == ["u/p/a"]


def test_filter_documents_sorts_without_mutating_original_listing():
    documents = [
        {"name": "b" * 32 + "_Zulu.pdf"},
        {"name": "a" * 32 + "_alpha.pdf"},
    ]
    original = list(documents)
    ascending = docs.filter_documents(documents, sort_order="name_asc")
    descending = docs.filter_documents(documents, sort_order="name_desc")
    assert [docs.display_document_name(item["name"]) for item in ascending] == ["alpha.pdf", "Zulu.pdf"]
    assert [docs.display_document_name(item["name"]) for item in descending] == ["Zulu.pdf", "alpha.pdf"]
    assert documents == original


def test_filter_documents_rejects_unknown_sort_order():
    with pytest.raises(ValueError, match="Ordre de tri invalide"):
        docs.filter_documents([], sort_order="uploaded")


def test_filter_documents_sorts_by_upload_date_and_keeps_unknown_dates_last():
    documents = [
        {"name": "old.pdf", "created_at": "2026-01-01T10:00:00Z"},
        {"name": "new.pdf", "created_at": "2026-03-01T10:00:00+00:00"},
        {"name": "middle.pdf", "created_at": "2026-02-01T10:00:00Z"},
        {"name": "unknown.pdf"},
        {"name": "invalid.pdf", "created_at": "not-a-date"},
    ]

    newest = docs.filter_documents(documents, sort_order="newest")
    oldest = docs.filter_documents(documents, sort_order="oldest")

    assert [item["name"] for item in newest] == [
        "new.pdf", "middle.pdf", "old.pdf", "unknown.pdf", "invalid.pdf"
    ]
    assert [item["name"] for item in oldest] == [
        "old.pdf", "middle.pdf", "new.pdf", "unknown.pdf", "invalid.pdf"
    ]


def test_filter_documents_treats_naive_storage_dates_as_utc():
    documents = [
        {"name": "later.pdf", "created_at": "2026-02-01T10:00:00"},
        {"name": "earlier.pdf", "created_at": "2026-01-01T10:00:00Z"},
    ]

    result = docs.filter_documents(documents, sort_order="oldest")

    assert [item["name"] for item in result] == ["earlier.pdf", "later.pdf"]


def test_filter_documents_rejects_unknown_date_sort_order():
    with pytest.raises(ValueError, match="Ordre de tri invalide"):
        docs.filter_documents([], sort_order="uploaded")

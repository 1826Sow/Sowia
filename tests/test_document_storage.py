"""Tests for private Supabase PDF storage ownership and validation."""
import pytest
import document_storage as docs


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


def test_upload_is_stored_under_authenticated_user_folder():
    client = FakeClient()
    path = docs.upload_document(client, User(), "Mon rapport.pdf", b"%PDF")
    assert path.startswith("user-123/personal/")
    assert path.endswith("_Mon_rapport.pdf")
    assert client.bucket.uploaded[1] == b"%PDF"
    assert client.bucket.uploaded[2]["content-type"] == "application/pdf"


def test_long_pdf_filename_keeps_pdf_extension_and_length_limit():
    filename = "a" * 140 + ".pdf"
    safe = docs._safe_filename(filename)
    assert len(safe) == 100
    assert safe.endswith(".pdf")


def test_list_documents_uses_only_authenticated_user_folder():
    client = FakeClient()
    result = docs.list_documents(client, User())
    assert client.bucket.listed == ["user-123", "user-123/personal"]
    assert len(result) == 2
    assert result[0]["path"] == "user-123/report.pdf"
    assert result[1]["path"] == "user-123/personal/report.pdf"


def test_download_rejects_another_users_path_before_storage_access():
    client = FakeClient()
    with pytest.raises(PermissionError):
        docs.download_document(client, User(), "other-user/report.pdf")
    assert client.bucket.downloaded is None


def test_professional_workspace_cannot_access_personal_document():
    client = FakeClient()
    with pytest.raises(ValueError, match="Chemin de document invalide"):
        docs.download_document(client, User(), "user-123/personal/report.pdf", "professional")
    assert client.bucket.downloaded is None


def test_delete_rejects_path_traversal():
    client = FakeClient()
    with pytest.raises(ValueError):
        docs.delete_document(client, User(), "user-123/../private.pdf")
    assert client.bucket.removed is None


def test_upload_rejects_non_pdf_and_oversized_files_before_storage_access():
    client = FakeClient()
    with pytest.raises(ValueError, match="PDF"):
        docs.upload_document(client, User(), "notes.txt", b"hello")
    with pytest.raises(ValueError, match="10 Mo"):
        docs.upload_document(client, User(), "large.pdf", b"x" * (docs.MAX_DOCUMENT_BYTES + 1))
    assert client.bucket.uploaded is None


def test_storage_requires_authenticated_user():
    with pytest.raises(PermissionError, match="Connexion requise"):
        docs.list_documents(FakeClient(), None)

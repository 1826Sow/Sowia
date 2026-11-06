"""Tests for private Supabase PDF storage ownership and validation."""
import pytest
import document_storage as docs


class User:
    id = "user-123"


class FakeBucket:
    def __init__(self):
        self.uploaded = None
        self.listed = None
        self.downloaded = None
        self.removed = None

    def upload(self, path, content, file_options=None):
        self.uploaded = (path, content, file_options)
        return {"path": path}

    def list(self, prefix):
        self.listed = prefix
        return [{"name": "report.pdf"}]

    def download(self, path):
        self.downloaded = path
        return b"%PDF-1.7"

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
    content = b"%PDF-1.7\nvalid test payload"
    path = docs.upload_document(client, User(), "Mon rapport.pdf", content)
    assert path.startswith("user-123/")
    assert path.endswith("_Mon_rapport.pdf")
    assert client.bucket.uploaded[1] == content
    assert client.bucket.uploaded[2]["content-type"] == "application/pdf"


def test_list_documents_uses_only_authenticated_user_folder():
    client = FakeClient()
    docs.list_documents(client, User())
    assert client.bucket.listed == "user-123"


def test_download_rejects_another_users_path_before_storage_access():
    client = FakeClient()
    with pytest.raises(PermissionError):
        docs.download_document(client, User(), "other-user/report.pdf")
    assert client.bucket.downloaded is None


def test_delete_rejects_path_traversal():
    client = FakeClient()
    with pytest.raises(ValueError):
        docs.delete_document(client, User(), "user-123/../private.pdf")
    assert client.bucket.removed is None


def test_upload_rejects_non_pdf_oversized_and_fake_pdf_before_storage_access():
    client = FakeClient()
    with pytest.raises(ValueError, match="PDF"):
        docs.upload_document(client, User(), "notes.txt", b"hello")
    with pytest.raises(ValueError, match="10 Mo"):
        docs.upload_document(client, User(), "large.pdf", b"%PDF-" + b"x" * docs.MAX_DOCUMENT_BYTES)
    with pytest.raises(ValueError, match="pas un PDF valide"):
        docs.upload_document(client, User(), "fake.pdf", b"not really a PDF")
    assert client.bucket.uploaded is None


def test_storage_requires_authenticated_user():
    with pytest.raises(PermissionError, match="Connexion requise"):
        docs.list_documents(FakeClient(), None)

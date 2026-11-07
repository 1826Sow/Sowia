"""Tests for private Supabase PDF storage ownership and workspace validation."""
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


def test_upload_is_stored_under_user_and_selected_workspace():
    client = FakeClient()
    path = docs.upload_document(client, User(), "Mon rapport.pdf", b"%PDF", "professional")
    assert path.startswith("user-123/professional/")
    assert path.endswith("_Mon_rapport.pdf")
    assert client.bucket.uploaded[1] == b"%PDF"
    assert client.bucket.uploaded[2]["content-type"] == "application/pdf"


def test_personal_document_listing_keeps_legacy_and_new_personal_folders():
    client = FakeClient()
    result = docs.list_documents(client, User(), "personal")
    assert client.bucket.listed == ["user-123", "user-123/personal"]
    assert len(result) == 2
    assert result[0]["path"] == "user-123/report.pdf"
    assert result[1]["path"] == "user-123/personal/report.pdf"


def test_professional_listing_never_reads_personal_or_legacy_files():
    client = FakeClient()
    result = docs.list_documents(client, User(), "professional")
    assert client.bucket.listed == ["user-123/professional"]
    assert result[0]["path"] == "user-123/professional/report.pdf"


def test_download_rejects_another_users_path_before_storage_access():
    client = FakeClient()
    with pytest.raises(PermissionError):
        docs.download_document(client, User(), "other-user/report.pdf")
    assert client.bucket.downloaded is None


def test_download_rejects_other_workspace_path():
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

"""Tests for private PDF storage ownership and workspace isolation."""
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
        return b"%PDF-1.4"

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
    path = docs.upload_document(client, User(), "Mon rapport.pdf", b"%PDF-1.4", workspace)
    assert path.startswith(f"user-123/{workspace}/")
    assert path.endswith("_Mon_rapport.pdf")
    assert client.bucket.uploaded[1] == b"%PDF-1.4"
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


def test_upload_rejects_invalid_pdf_content_before_storage_access():
    client = FakeClient()
    with pytest.raises(ValueError, match="PDF valide"):
        docs.upload_document(client, User(), "fake.pdf", b"ceci n'est pas un PDF")
    assert client.bucket.uploaded is None


@pytest.mark.parametrize("filename", [".pdf", "....pdf", "___ .pdf"])
def test_upload_rejects_pdf_filename_without_a_real_name(filename):
    with pytest.raises(ValueError, match="Nom de fichier invalide"):
        docs.upload_document(FakeClient(), User(), filename, b"%PDF-1.4")


def test_safe_filename_preserves_pdf_extension_when_cleaning():
    assert docs._safe_filename("rapport avec accents éè.pdf") == "rapport_avec_accents___.pdf"


def test_storage_requires_authenticated_user():
    with pytest.raises(PermissionError, match="Connexion requise"):
        docs.list_documents(FakeClient(), None)

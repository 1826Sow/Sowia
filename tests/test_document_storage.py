"""Tests for private Supabase PDF storage ownership and validation."""
from io import BytesIO

import pytest
from reportlab.pdfgen import canvas

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
        return make_pdf()

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


def make_pdf():
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)
    pdf.drawString(72, 720, "SOW IA test document")
    pdf.save()
    return buffer.getvalue()


def test_upload_is_stored_under_authenticated_user_folder():
    client = FakeClient()
    content = make_pdf()
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
    with pytest.raises(ValueError, match="PDF"):
        docs.upload_document(client, User(), "fake.pdf", b"%PDF-1.7\\nnot really a PDF")
    assert client.bucket.uploaded is None


def test_upload_rejects_encrypted_pdf():
    from reportlab.lib.pdfencrypt import StandardEncryption

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, encrypt=StandardEncryption("secret"))
    pdf.drawString(72, 720, "Protected")
    pdf.save()
    with pytest.raises(ValueError, match="mot de passe"):
        docs.upload_document(FakeClient(), User(), "protected.pdf", buffer.getvalue())


def test_storage_requires_authenticated_user():
    with pytest.raises(PermissionError, match="Connexion requise"):
        docs.list_documents(FakeClient(), None)

def test_optional_sql_has_restrictive_guard_for_existing_storage_policies():
    from pathlib import Path

    sql = (Path(__file__).resolve().parents[1] / "supabase_optional_features.sql").read_text()
    assert 'as restrictive' in sql.lower()
    assert '"SOW IA enforce private PDF folder isolation"' in sql
    assert "bucket_id <> 'sowia-private-documents'" in sql
    assert "(select auth.uid())::text" in sql

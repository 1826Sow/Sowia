"""Regression tests for the Android-compatible direct PDF upload path."""
from contextlib import nullcontext
from types import SimpleNamespace

import requests

import direct_pdf_upload as uploader


class FakeStreamlit:
    def __init__(self, selected=None):
        self.selected = selected
        self.session_state = {}
        self.messages = []

    def file_uploader(self, *args, **kwargs):
        assert kwargs["type"] is None
        return self.selected

    def caption(self, message):
        self.messages.append(("caption", message))

    def error(self, message):
        self.messages.append(("error", message))

    def success(self, message):
        self.messages.append(("success", message))

    def spinner(self, _message):
        return nullcontext()


class FakeUpload:
    def __init__(self, name="document.pdf", payload=b"%PDF-1.7\\ncontent"):
        self.name = name
        self._payload = payload

    def getvalue(self):
        return self._payload


class FakeResponse:
    def raise_for_status(self):
        return None


def test_create_signed_pdf_upload_creates_user_and_workspace_scoped_path():
    class Bucket:
        def create_signed_upload_url(self, path):
            self.path = path
            return {"signed_url": "https://storage.example/upload?token=short-lived"}

    class Storage:
        def __init__(self):
            self.bucket = Bucket()

        def from_(self, name):
            assert name == uploader.BUCKET_NAME
            return self.bucket

    class User:
        id = "user-123"

    class Client:
        def __init__(self):
            self.storage = Storage()

    client = Client()
    path, url = uploader.create_signed_pdf_upload(client, User(), "professional")

    assert path.startswith("user-123/professional/analyse_")
    assert path.endswith(".pdf")
    assert url == "https://storage.example/upload?token=short-lived"


def test_valid_pdf_is_sent_to_supabase_signed_upload_url(monkeypatch):
    payload = b"%PDF-1.7\\nvalid document"
    fake_st = FakeStreamlit(FakeUpload(payload=payload))
    calls = []
    monkeypatch.setattr(uploader, "st", fake_st)

    def fake_put(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse()

    monkeypatch.setattr(uploader.requests, "put", fake_put)
    result = uploader.render_direct_pdf_upload(
        "https://storage.example/upload?token=short-lived",
        key="test_upload",
    )

    assert result.uploaded is True
    assert result.file_name == "document.pdf"
    assert result.file_size == len(payload)
    assert result.upload_error is None
    assert calls[0][0] == "https://storage.example/upload?token=short-lived"
    assert calls[0][1]["data"] == payload
    assert calls[0][1]["headers"]["Content-Type"] == "application/pdf"
    assert fake_st.session_state["test_upload_uploaded_fingerprint"]


def test_no_selection_does_not_attempt_upload(monkeypatch):
    fake_st = FakeStreamlit()
    monkeypatch.setattr(uploader, "st", fake_st)
    monkeypatch.setattr(
        uploader.requests,
        "put",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("unexpected upload")),
    )

    result = uploader.render_direct_pdf_upload("https://storage.example/upload")

    assert result.uploaded is False
    assert result.file_name is None
    assert result.upload_error is None


def test_non_pdf_extension_is_rejected_before_network_upload(monkeypatch):
    fake_st = FakeStreamlit(FakeUpload(name="notes.txt"))
    monkeypatch.setattr(uploader, "st", fake_st)
    monkeypatch.setattr(
        uploader.requests,
        "put",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("unexpected upload")),
    )

    result = uploader.render_direct_pdf_upload("https://storage.example/upload")

    assert result.uploaded is False
    assert "Format non PDF" in result.upload_error


def test_invalid_pdf_signature_is_rejected_before_network_upload(monkeypatch):
    fake_st = FakeStreamlit(FakeUpload(payload=b"not a PDF"))
    monkeypatch.setattr(uploader, "st", fake_st)
    monkeypatch.setattr(
        uploader.requests,
        "put",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("unexpected upload")),
    )

    result = uploader.render_direct_pdf_upload("https://storage.example/upload")

    assert result.uploaded is False
    assert "Signature PDF invalide" in result.upload_error


def test_pdf_over_10_mb_is_rejected_before_network_upload(monkeypatch):
    fake_st = FakeStreamlit(FakeUpload(payload=b"%PDF-" + b"x" * uploader.MAX_PDF_BYTES))
    monkeypatch.setattr(uploader, "st", fake_st)
    monkeypatch.setattr(
        uploader.requests,
        "put",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("unexpected upload")),
    )

    result = uploader.render_direct_pdf_upload("https://storage.example/upload")

    assert result.uploaded is False
    assert "Taille PDF invalide" in result.upload_error


def test_missing_signed_url_is_reported_without_network_upload(monkeypatch):
    fake_st = FakeStreamlit(FakeUpload())
    monkeypatch.setattr(uploader, "st", fake_st)
    monkeypatch.setattr(
        uploader.requests,
        "put",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("unexpected upload")),
    )

    result = uploader.render_direct_pdf_upload(None)

    assert result.uploaded is False
    assert "Lien temporaire Supabase" in result.upload_error


def test_supabase_upload_error_is_reported_and_not_marked_uploaded(monkeypatch):
    fake_st = FakeStreamlit(FakeUpload())
    monkeypatch.setattr(uploader, "st", fake_st)

    def fail_put(*_args, **_kwargs):
        raise requests.Timeout("upload timed out")

    monkeypatch.setattr(uploader.requests, "put", fail_put)
    result = uploader.render_direct_pdf_upload("https://storage.example/upload")

    assert result.uploaded is False
    assert "Transfert Supabase refusé" in result.upload_error
    assert "test_upload_uploaded_fingerprint" not in fake_st.session_state

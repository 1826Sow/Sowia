"""Regression tests for the Android-compatible direct PDF upload path."""
from contextlib import nullcontext

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


class FakeBucket:
    def __init__(self, error=None):
        self.calls = []
        self.error = error

    def create_signed_upload_url(self, path):
        self.path = path
        return {"signed_url": "https://storage.example/upload?token=short-lived"}

    def upload_to_signed_url(self, path, token, payload, file_options=None):
        self.calls.append((path, token, payload, file_options))
        if self.error:
            raise self.error
        return {"path": path}


class FakeStorage:
    def __init__(self, bucket=None):
        self.bucket = bucket or FakeBucket()

    def from_(self, name):
        assert name == uploader.BUCKET_NAME
        return self.bucket


class FakeClient:
    def __init__(self, bucket=None):
        self.storage = FakeStorage(bucket)


class FakeUser:
    id = "user-123"


def test_create_signed_pdf_upload_creates_user_and_workspace_scoped_path():
    client = FakeClient()
    path, url = uploader.create_signed_pdf_upload(client, FakeUser(), "professional")

    assert path.startswith("user-123/professional/analyse_")
    assert path.endswith(".pdf")
    assert url == "https://storage.example/upload?token=short-lived"
    assert client.storage.bucket.path == path


def test_valid_pdf_uses_supabase_sdk_signed_upload(monkeypatch):
    payload = b"%PDF-1.7\\nvalid document"
    fake_st = FakeStreamlit(FakeUpload(payload=payload))
    client = FakeClient()
    monkeypatch.setattr(uploader, "st", fake_st)

    result = uploader.render_direct_pdf_upload(
        "https://storage.example/upload?token=short-lived",
        key="test_upload",
        client=client,
        path="user-123/personal/document.pdf",
    )

    assert result.uploaded is True
    assert result.file_name == "document.pdf"
    assert result.file_size == len(payload)
    assert result.upload_error is None
    assert client.storage.bucket.calls == [(
        "user-123/personal/document.pdf",
        "short-lived",
        payload,
        {"content-type": "application/pdf", "cache-control": "3600"},
    )]
    assert fake_st.session_state["test_upload_uploaded_fingerprint"]


def test_captured_android_selection_survives_widget_rerun(monkeypatch):
    payload = b"%PDF-1.7\\nselected before rerun"
    fake_st = FakeStreamlit()
    fake_st.session_state["test_upload_captured_file"] = {
        "name": "document.pdf",
        "payload": payload,
    }
    client = FakeClient()
    monkeypatch.setattr(uploader, "st", fake_st)

    result = uploader.render_direct_pdf_upload(
        "https://storage.example/upload?token=short-lived",
        key="test_upload",
        client=client,
        path="user-123/personal/document.pdf",
    )

    assert result.uploaded is True
    assert result.file_name == "document.pdf"
    assert result.file_size == len(payload)
    assert client.storage.bucket.calls[0][2] == payload
    assert "test_upload_captured_file" not in fake_st.session_state


def test_no_selection_does_not_attempt_upload(monkeypatch):
    fake_st = FakeStreamlit()
    monkeypatch.setattr(uploader, "st", fake_st)

    result = uploader.render_direct_pdf_upload("https://storage.example/upload")

    assert result.uploaded is False
    assert result.file_name is None
    assert result.upload_error is None


def test_non_pdf_extension_is_rejected_before_upload(monkeypatch):
    fake_st = FakeStreamlit(FakeUpload(name="notes.txt"))
    monkeypatch.setattr(uploader, "st", fake_st)

    result = uploader.render_direct_pdf_upload("https://storage.example/upload")

    assert result.uploaded is False
    assert "Format non PDF" in result.upload_error


def test_invalid_pdf_signature_is_rejected_before_upload(monkeypatch):
    fake_st = FakeStreamlit(FakeUpload(payload=b"not a PDF"))
    monkeypatch.setattr(uploader, "st", fake_st)

    result = uploader.render_direct_pdf_upload("https://storage.example/upload")

    assert result.uploaded is False
    assert "Signature PDF invalide" in result.upload_error


def test_pdf_over_10_mb_is_rejected_before_upload(monkeypatch):
    fake_st = FakeStreamlit(FakeUpload(payload=b"%PDF-" + b"x" * uploader.MAX_PDF_BYTES))
    monkeypatch.setattr(uploader, "st", fake_st)

    result = uploader.render_direct_pdf_upload("https://storage.example/upload")

    assert result.uploaded is False
    assert "Taille PDF invalide" in result.upload_error


def test_signed_upload_requires_token_client_and_path(monkeypatch):
    fake_st = FakeStreamlit(FakeUpload())
    monkeypatch.setattr(uploader, "st", fake_st)

    result = uploader.render_direct_pdf_upload("https://storage.example/upload")

    assert result.uploaded is False
    assert "Autorisation temporaire Supabase incomplète" in result.upload_error


def test_supabase_sdk_error_is_not_marked_uploaded(monkeypatch):
    fake_st = FakeStreamlit(FakeUpload())
    bucket = FakeBucket(error=RuntimeError("storage unavailable"))
    client = FakeClient(bucket)
    monkeypatch.setattr(uploader, "st", fake_st)

    result = uploader.render_direct_pdf_upload(
        "https://storage.example/upload?token=short-lived",
        key="test_upload",
        client=client,
        path="user-123/personal/document.pdf",
    )

    assert result.uploaded is False
    assert "Transfert Supabase refusé" in result.upload_error
    assert "test_upload_uploaded_fingerprint" not in fake_st.session_state

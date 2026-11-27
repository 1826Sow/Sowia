"""Regression tests for the browser-native direct PDF upload path."""
from contextlib import nullcontext

import direct_pdf_upload as uploader


class FakeStreamlit:
    def __init__(self, selected=None, *, clear_widget_after_callback=False):
        self.selected = selected
        self.clear_widget_after_callback = clear_widget_after_callback
        self.session_state = {}
        self.messages = []

    def file_uploader(self, *args, **kwargs):
        assert kwargs["type"] is None
        callback = kwargs.get("on_change")
        if callback:
            callback()
        if self.clear_widget_after_callback:
            self.session_state.pop(kwargs["key"], None)
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
        return {"token": "short-lived"}

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


def test_valid_pdf_creates_signed_token_after_browser_selection(monkeypatch):
    payload = b"%PDF-1.7\\nvalid document"
    fake_st = FakeStreamlit(FakeUpload(payload=payload))
    client = FakeClient()
    monkeypatch.setattr(uploader, "st", fake_st)

    result = uploader.render_direct_pdf_upload(
        client, FakeUser(), "personal", key="test_upload"
    )

    assert result.uploaded is True
    assert result.file_name == "document.pdf"
    assert result.file_size == len(payload)
    assert result.file_path == client.storage.bucket.path
    assert client.storage.bucket.calls == [(
        result.file_path,
        "short-lived",
        payload,
        {"content-type": "application/pdf", "cache-control": "3600"},
    )]
    assert fake_st.session_state["test_upload_uploaded_fingerprint"]


def test_file_in_session_state_is_used_when_widget_return_is_empty(monkeypatch):
    payload = b"%PDF-1.7\\nreceived in widget state"
    fake_st = FakeStreamlit()
    fake_st.session_state["test_upload_file"] = FakeUpload(payload=payload)
    client = FakeClient()
    monkeypatch.setattr(uploader, "st", fake_st)

    result = uploader.render_direct_pdf_upload(
        client, FakeUser(), "personal", key="test_upload"
    )

    assert result.uploaded is True
    assert client.storage.bucket.calls[0][2] == payload


def test_upload_callback_preserves_pdf_when_widget_value_disappears(monkeypatch):
    payload = b"%PDF-1.7\\nselected in uploader callback"
    fake_st = FakeStreamlit(clear_widget_after_callback=True)
    fake_st.session_state["test_upload_file"] = FakeUpload(payload=payload)
    client = FakeClient()
    monkeypatch.setattr(uploader, "st", fake_st)

    result = uploader.render_direct_pdf_upload(
        client, FakeUser(), "personal", key="test_upload"
    )

    assert result.uploaded is True
    assert client.storage.bucket.calls[0][2] == payload
    assert "test_upload_captured_file" not in fake_st.session_state


def test_captured_file_survives_widget_rerun(monkeypatch):
    payload = b"%PDF-1.7\\nselected before rerun"
    fake_st = FakeStreamlit()
    fake_st.session_state["test_upload_captured_file"] = {
        "name": "document.pdf", "payload": payload,
    }
    client = FakeClient()
    monkeypatch.setattr(uploader, "st", fake_st)

    result = uploader.render_direct_pdf_upload(
        client, FakeUser(), "personal", key="test_upload"
    )

    assert result.uploaded is True
    assert result.file_size == len(payload)
    assert client.storage.bucket.calls[0][2] == payload
    assert "test_upload_captured_file" not in fake_st.session_state


def test_no_selection_does_not_attempt_upload(monkeypatch):
    fake_st = FakeStreamlit()
    monkeypatch.setattr(uploader, "st", fake_st)
    result = uploader.render_direct_pdf_upload(FakeClient(), FakeUser())
    assert result.uploaded is False
    assert result.file_name is None
    assert result.upload_error is None


def test_non_pdf_extension_is_rejected_before_upload(monkeypatch):
    fake_st = FakeStreamlit(FakeUpload(name="notes.txt"))
    monkeypatch.setattr(uploader, "st", fake_st)
    result = uploader.render_direct_pdf_upload(FakeClient(), FakeUser())
    assert result.uploaded is False
    assert "Format non PDF" in result.upload_error


def test_invalid_pdf_signature_is_rejected_before_upload(monkeypatch):
    fake_st = FakeStreamlit(FakeUpload(payload=b"not a PDF"))
    monkeypatch.setattr(uploader, "st", fake_st)
    result = uploader.render_direct_pdf_upload(FakeClient(), FakeUser())
    assert result.uploaded is False
    assert "Signature PDF invalide" in result.upload_error


def test_pdf_over_10_mb_is_rejected_before_upload(monkeypatch):
    fake_st = FakeStreamlit(FakeUpload(payload=b"%PDF-" + b"x" * uploader.MAX_PDF_BYTES))
    monkeypatch.setattr(uploader, "st", fake_st)
    result = uploader.render_direct_pdf_upload(FakeClient(), FakeUser())
    assert result.uploaded is False
    assert "Taille PDF invalide" in result.upload_error


def test_supabase_sdk_error_is_not_marked_uploaded(monkeypatch):
    fake_st = FakeStreamlit(FakeUpload())
    client = FakeClient(FakeBucket(error=RuntimeError("storage unavailable")))
    monkeypatch.setattr(uploader, "st", fake_st)
    result = uploader.render_direct_pdf_upload(client, FakeUser())
    assert result.uploaded is False
    assert "Transfert Supabase refusé" in result.upload_error
    assert "sowia_pdf_upload_uploaded_fingerprint" not in fake_st.session_state

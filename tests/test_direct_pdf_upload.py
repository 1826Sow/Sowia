"""Regression tests for the private, signed-URL PDF upload flow."""
from contextlib import nullcontext
from types import SimpleNamespace

import requests

import direct_pdf_upload


class _FakeStreamlit:
    def __init__(self, selected_file):
        self.selected_file = selected_file
        self.session_state = {}
        self.messages = []

    def file_uploader(self, *args, **kwargs):
        return self.selected_file

    def caption(self, message):
        self.messages.append(("caption", message))

    def error(self, message):
        self.messages.append(("error", message))

    def success(self, message):
        self.messages.append(("success", message))

    def spinner(self, message):
        self.messages.append(("spinner", message))
        return nullcontext()


def _file(name="rapport.pdf", payload=b"%PDF-1.7\ncontenu de test"):
    return SimpleNamespace(name=name, getvalue=lambda: payload)


def test_empty_picker_does_not_start_an_upload(monkeypatch):
    fake_st = _FakeStreamlit(None)
    monkeypatch.setattr(direct_pdf_upload, "st", fake_st)
    calls = []
    monkeypatch.setattr(direct_pdf_upload.requests, "put", lambda *a, **k: calls.append(a))

    result = direct_pdf_upload.render_direct_pdf_upload(
        "https://storage.example/signed", key="test_empty"
    )

    assert result.uploaded is False
    assert result.upload_error is None
    assert calls == []


def test_rejects_non_pdf_filename_without_upload(monkeypatch):
    fake_st = _FakeStreamlit(_file("notes.txt"))
    monkeypatch.setattr(direct_pdf_upload, "st", fake_st)
    calls = []
    monkeypatch.setattr(direct_pdf_upload.requests, "put", lambda *a, **k: calls.append(a))

    result = direct_pdf_upload.render_direct_pdf_upload(
        "https://storage.example/signed", key="test_extension"
    )

    assert result.uploaded is False
    assert result.upload_error == "Format non PDF."
    assert calls == []


def test_rejects_oversized_pdf_without_upload(monkeypatch):
    payload = b"%PDF-1.7\n" + b"x" * direct_pdf_upload.MAX_PDF_BYTES
    fake_st = _FakeStreamlit(_file(payload=payload))
    monkeypatch.setattr(direct_pdf_upload, "st", fake_st)
    calls = []
    monkeypatch.setattr(direct_pdf_upload.requests, "put", lambda *a, **k: calls.append(a))

    result = direct_pdf_upload.render_direct_pdf_upload(
        "https://storage.example/signed", key="test_size"
    )

    assert result.uploaded is False
    assert result.upload_error == "Taille PDF invalide."
    assert calls == []


def test_rejects_invalid_pdf_signature_without_upload(monkeypatch):
    fake_st = _FakeStreamlit(_file(payload=b"not a pdf"))
    monkeypatch.setattr(direct_pdf_upload, "st", fake_st)
    calls = []
    monkeypatch.setattr(direct_pdf_upload.requests, "put", lambda *a, **k: calls.append(a))

    result = direct_pdf_upload.render_direct_pdf_upload(
        "https://storage.example/signed", key="test_signature"
    )

    assert result.uploaded is False
    assert result.upload_error == "Signature PDF invalide."
    assert calls == []


def test_valid_pdf_upload_is_sent_once_and_deduplicated(monkeypatch):
    fake_st = _FakeStreamlit(_file())
    monkeypatch.setattr(direct_pdf_upload, "st", fake_st)
    calls = []

    class _Response:
        def raise_for_status(self):
            return None

    def fake_put(url, **kwargs):
        calls.append((url, kwargs))
        return _Response()

    monkeypatch.setattr(direct_pdf_upload.requests, "put", fake_put)

    first = direct_pdf_upload.render_direct_pdf_upload(
        "https://storage.example/signed", key="test_valid"
    )
    second = direct_pdf_upload.render_direct_pdf_upload(
        "https://storage.example/signed", key="test_valid"
    )

    assert first.uploaded is True
    assert second.uploaded is True
    assert first.file_name == "rapport.pdf"
    assert len(calls) == 1
    assert calls[0][1]["headers"]["Content-Type"] == "application/pdf"
    assert calls[0][1]["headers"]["x-upsert"] == "false"


def test_invalid_signed_url_and_network_failure_are_reported(monkeypatch):
    fake_st = _FakeStreamlit(_file())
    monkeypatch.setattr(direct_pdf_upload, "st", fake_st)
    calls = []
    monkeypatch.setattr(direct_pdf_upload.requests, "put", lambda *a, **k: calls.append(a))

    invalid_url = direct_pdf_upload.render_direct_pdf_upload(
        "http://storage.example/signed", key="test_bad_url"
    )
    assert invalid_url.uploaded is False
    assert "invalide" in invalid_url.upload_error
    assert calls == []

    monkeypatch.setattr(
        direct_pdf_upload.requests,
        "put",
        lambda *a, **k: (_ for _ in ()).throw(requests.RequestException("réseau indisponible")),
    )
    failed = direct_pdf_upload.render_direct_pdf_upload(
        "https://storage.example/signed", key="test_network"
    )
    assert failed.uploaded is False
    assert "réseau indisponible" in failed.upload_error

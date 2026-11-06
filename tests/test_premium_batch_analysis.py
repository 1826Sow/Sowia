"""Tests for Premium batch PDF analysis access and limits."""
from io import BytesIO

import pytest
from pypdf import PdfWriter

import premium_batch_analysis


def test_batch_analysis_checks_entitlement_before_ai(monkeypatch):
    calls = []

    def guard(client, user, feature):
        calls.append(("guard", client, user, feature))

    def answer(messages, **kwargs):
        calls.append(("answer", messages, kwargs))
        return "Comparaison terminée"

    monkeypatch.setattr(premium_batch_analysis, "require_feature_access", guard)
    result = premium_batch_analysis.analyze_pdf_batch(
        "client", "user",
        [("a.pdf", "Texte A"), ("b.pdf", "Texte B")],
        answer,
    )
    assert result == "Comparaison terminée"
    assert calls[0] == ("guard", "client", "user", "batch_pdf_analysis")
    assert calls[1][0] == "answer"
    assert "DOCUMENT 1 — a.pdf" in calls[1][2]["document_context"]
    assert "DOCUMENT 2 — b.pdf" in calls[1][2]["document_context"]
    assert calls[1][2]["user_mode"] == "Professionnel"


def test_batch_analysis_denies_before_sending_text_to_ai(monkeypatch):
    def deny(*args, **kwargs):
        raise PermissionError("Premium requis")

    def unexpected_answer(*args, **kwargs):
        raise AssertionError("AI must not be called without Premium")

    monkeypatch.setattr(premium_batch_analysis, "require_feature_access", deny)
    with pytest.raises(PermissionError, match="Premium requis"):
        premium_batch_analysis.analyze_pdf_batch(
            "client", "user", [("a.pdf", "secret A"), ("b.pdf", "secret B")],
            unexpected_answer,
        )


@pytest.mark.parametrize("documents", [
    [],
    [("a.pdf", "Texte")],
    [("a.pdf", "A"), ("b.pdf", "B"), ("c.pdf", "C"),
     ("d.pdf", "D"), ("e.pdf", "E"), ("f.pdf", "F")],
])
def test_batch_analysis_enforces_document_count(documents):
    with pytest.raises(ValueError, match="2 et 5"):
        premium_batch_analysis.analyze_pdf_batch("client", "user", documents, lambda *a, **k: "")


def test_batch_analysis_rejects_empty_document_text():
    with pytest.raises(ValueError, match="texte extractible"):
        premium_batch_analysis.analyze_pdf_batch(
            "client", "user", [("a.pdf", "Texte"), ("b.pdf", "")],
            lambda *a, **k: "",
        )


def test_batch_analysis_caps_total_context(monkeypatch):
    monkeypatch.setattr(premium_batch_analysis, "require_feature_access", lambda *a, **k: None)
    received = {}

    def answer(messages, **kwargs):
        received.update(kwargs)
        return "ok"

    documents = [(f"{i}.pdf", "x" * 7000) for i in range(5)]
    premium_batch_analysis.analyze_pdf_batch("client", "user", documents, answer)
    assert len(received["document_context"]) <= premium_batch_analysis.MAX_BATCH_TOTAL_CHARS + 200


def valid_pdf_bytes():
    buffer = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.write(buffer)
    return buffer.getvalue()


class FakeUploadedFile:
    def __init__(self, name, payload):
        self.name = name
        self.payload = payload
        self.position = 0

    def getvalue(self):
        return self.payload

    def seek(self, position):
        self.position = position


def test_batch_upload_preparation_checks_pdf_signature_size_and_resets_pointer():
    calls = []

    def extract(uploaded, max_chars):
        calls.append((uploaded.name, max_chars, uploaded.position))
        return "Texte extrait"

    files = [
        FakeUploadedFile("a.pdf", valid_pdf_bytes()),
        FakeUploadedFile("b.pdf", valid_pdf_bytes()),
    ]
    prepared = premium_batch_analysis.prepare_pdf_batch_uploads(files, extract)
    assert prepared == [("a.pdf", "Texte extrait"), ("b.pdf", "Texte extrait")]
    assert calls == [("a.pdf", 7000, 0), ("b.pdf", 7000, 0)]


@pytest.mark.parametrize("payload,message", [
    (b"", "vide"),
    (b"not a PDF", "pas un PDF valide"),
    (b"%PDF-" + b"x" * (premium_batch_analysis.MAX_BATCH_FILE_BYTES + 1), "10 Mo maximum"),
])
def test_batch_upload_preparation_rejects_invalid_or_oversized_files(payload, message):
    files = [
        FakeUploadedFile("a.pdf", valid_pdf_bytes()),
        FakeUploadedFile("b.pdf", payload),
    ]
    with pytest.raises(ValueError, match=message):
        premium_batch_analysis.prepare_pdf_batch_uploads(files, lambda *a, **k: "texte")


def test_batch_upload_preparation_rejects_malformed_pdf_before_extraction():
    files = [
        FakeUploadedFile("a.pdf", b"%PDF-1.7\\nnot a valid PDF structure"),
        FakeUploadedFile("b.pdf", valid_pdf_bytes()),
    ]
    extraction_calls = []

    def extract(*args, **kwargs):
        extraction_calls.append(True)
        return "texte"

    with pytest.raises(ValueError, match="PDF illisible ou mal formé"):
        premium_batch_analysis.prepare_pdf_batch_uploads(files, extract)
    assert extraction_calls == []


def test_app_checks_batch_entitlement_before_pdf_parsing():
    """Keep the UI gate ahead of CPU-intensive parsing of uploaded PDFs."""
    app_source = (ROOT / "app.py").read_text(encoding="utf-8")
    batch_section = app_source.split('st.markdown("#### Analyse de plusieurs PDF — Premium")', 1)[1]
    batch_section = batch_section.split('elif page == "Créer un PDF":', 1)[0]
    guard = batch_section.index(
        'require_feature_access(\n                        supabase_client, current_user, "batch_pdf_analysis"'
    )
    parsing = batch_section.index("prepare_pdf_batch_uploads(")
    assert guard < parsing

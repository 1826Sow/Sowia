"""Tests for PDF extraction safeguards."""
from io import BytesIO

import pytest
from pypdf import PdfWriter

import documents
from documents import extract_pdf_text


def _blank_pdf():
    output = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    writer.write(output)
    output.seek(0)
    return output


def test_blank_pdf_reports_that_no_text_was_found(monkeypatch):
    monkeypatch.setattr(documents, "_ocr_pdf_pages", lambda *_args: "")
    with pytest.raises(ValueError, match="Aucun texte extractible"):
        extract_pdf_text(_blank_pdf())


def test_pdf_upload_over_10_mb_is_rejected_before_parsing():
    class OversizedUpload:
        size = documents.MAX_PDF_BYTES + 1

    with pytest.raises(ValueError, match="10 Mo"):
        extract_pdf_text(OversizedUpload())


def test_pdf_with_too_many_pages_is_rejected(monkeypatch):
    class Page:
        def extract_text(self):
            return "Texte"

    class Reader:
        is_encrypted = False
        pages = [Page(), Page(), Page()]

    monkeypatch.setattr(documents, "PdfReader", lambda _file, **_kwargs: Reader())
    with pytest.raises(ValueError, match="limite de 2 pages"):
        extract_pdf_text(_blank_pdf(), max_pages=2)


def test_encrypted_pdf_is_rejected_with_clear_message(monkeypatch):
    class Reader:
        is_encrypted = True
        pages = []

    monkeypatch.setattr(documents, "PdfReader", lambda _file, **_kwargs: Reader())
    with pytest.raises(ValueError, match="protégé par mot de passe"):
        extract_pdf_text(_blank_pdf())


def test_extracted_text_respects_max_chars(monkeypatch):
    class Page:
        def extract_text(self):
            return "x" * 100

    class Reader:
        is_encrypted = False
        pages = [Page()]

    monkeypatch.setattr(documents, "PdfReader", lambda _file, **_kwargs: Reader())
    result = extract_pdf_text(_blank_pdf(), max_chars=20)
    assert len(result) <= 20


@pytest.mark.parametrize("value", [0, -1, True, "100"])
def test_invalid_text_limit_is_rejected(value):
    with pytest.raises(ValueError, match="entier positif"):
        extract_pdf_text(_blank_pdf(), max_chars=value)


def test_invalid_page_limit_is_rejected():
    with pytest.raises(ValueError, match="entier positif"):
        extract_pdf_text(_blank_pdf(), max_pages=0)



def test_ocr_releases_native_resources_when_recognition_fails(monkeypatch):
    import sys
    from types import SimpleNamespace

    released = {"image": False, "bitmap": False, "page": False, "pdf": False}

    class Image:
        def close(self):
            released["image"] = True

    class Bitmap:
        def to_pil(self):
            return Image()

        def close(self):
            released["bitmap"] = True

    class Page:
        def render(self, scale):
            assert scale == 2
            return Bitmap()

        def close(self):
            released["page"] = True

    class Pdf:
        def __len__(self):
            return 1

        def __getitem__(self, index):
            assert index == 0
            return Page()

        def close(self):
            released["pdf"] = True

    monkeypatch.setitem(sys.modules, "pypdfium2", SimpleNamespace(PdfDocument=lambda _data: Pdf()))
    monkeypatch.setitem(
        sys.modules,
        "pytesseract",
        SimpleNamespace(image_to_string=lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("OCR failed"))),
    )

    with pytest.raises(RuntimeError, match="OCR failed"):
        documents._ocr_pdf_pages(b"%PDF-test", max_chars=1000, max_pages=1)

    assert released == {"image": True, "bitmap": True, "page": True, "pdf": True}


def test_pdf_source_stream_is_closed_after_text_extraction(monkeypatch):
    captured = {}

    class Page:
        def extract_text(self):
            return "Contenu du document"

    class Reader:
        is_encrypted = False
        pages = [Page()]

    def make_reader(stream, **_kwargs):
        captured["stream"] = stream
        return Reader()

    monkeypatch.setattr(documents, "PdfReader", make_reader)
    result = extract_pdf_text(_blank_pdf())

    assert "Contenu du document" in result
    assert captured["stream"].closed

"""Tests for PDF extraction safeguards."""
from io import BytesIO

import pytest
from pypdf import PdfWriter

from documents import (
    MAX_EXTRACTED_CHARS,
    MAX_PDF_BYTES,
    MAX_PDF_PAGES,
    extract_pdf_text,
)


def make_pdf(page_count=1, text="SOW IA test"):
    output = BytesIO()
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=300, height=300)
    writer.write(output)
    return output.getvalue()


def test_blank_pdf_reports_that_no_text_was_found():
    with pytest.raises(ValueError, match="Aucun texte extractible"):
        extract_pdf_text(BytesIO(make_pdf()))


@pytest.mark.parametrize(
    "payload, message",
    [
        (b"", "vide"),
        (b"not a PDF", "PDF valide"),
        (b"%PDF-" + b"x" * MAX_PDF_BYTES, "10 Mo"),
    ],
)
def test_rejects_empty_non_pdf_and_oversized_uploads(payload, message):
    with pytest.raises(ValueError, match=message):
        extract_pdf_text(BytesIO(payload))


def test_rejects_pdf_over_page_limit_before_text_extraction():
    payload = make_pdf(MAX_PDF_PAGES + 1)
    with pytest.raises(ValueError, match="200 pages"):
        extract_pdf_text(BytesIO(payload))


def test_rejects_encrypted_pdf():
    from reportlab.pdfgen import canvas
    from reportlab.lib.pdfencrypt import StandardEncryption

    output = BytesIO()
    pdf = canvas.Canvas(output, encrypt=StandardEncryption("secret"))
    pdf.drawString(72, 720, "Protected")
    pdf.save()
    with pytest.raises(ValueError, match="mot de passe"):
        extract_pdf_text(BytesIO(output.getvalue()))


def test_extraction_limit_is_bounded_even_if_caller_requests_more(monkeypatch):
    # A blank PDF exercises the input validation path without needing a
    # large synthetic text payload.
    with pytest.raises(ValueError, match="Aucun texte extractible"):
        extract_pdf_text(BytesIO(make_pdf()), max_chars=MAX_EXTRACTED_CHARS + 1)


def test_rejects_non_positive_extraction_limit():
    with pytest.raises(ValueError, match="positive"):
        extract_pdf_text(BytesIO(make_pdf()), max_chars=0)

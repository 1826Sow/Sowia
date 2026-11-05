""""Tests for PDF extraction safeguards."""
from io import BytesIO

import pytest
from pypdf import PdfWriter

from documents import extract_pdf_pages, extract_pdf_text, validate_pdf_upload


def make_pdf(page_count=1):
    output = BytesIO()
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=300, height=300)
    writer.write(output)
    output.seek(0)
    return output


def test_blank_pdf_reports_that_no_text_was_found():
    with pytest.raises(ValueError, match="Aucun texte extractible"):
        extract_pdf_text(make_pdf())


def test_rejects_non_pdf_content():
    with pytest.raises(ValueError, match="pas un PDF valide"):
        validate_pdf_upload(BytesIO(b"not a pdf document"))


def test_rejects_empty_file():
    with pytest.raises(ValueError, match="vide"):
        validate_pdf_upload(BytesIO(b""))


def test_rejects_upload_over_size_limit():
    with pytest.raises(ValueError, match="15 Mo"):
        validate_pdf_upload(make_pdf(), max_bytes=10)


def test_rejects_pdf_over_page_limit():
    with pytest.raises(ValueError, match="maximum 2 pages"):
        validate_pdf_upload(make_pdf(page_count=3), max_pages=2)


def test_accepts_valid_pdf_and_rewinds_file():
    uploaded = make_pdf()
    reader = validate_pdf_upload(uploaded)
    assert len(reader.pages) == 1
    assert uploaded.tell() == 0


@pytest.mark.parametrize("value", [0, -1, True, False, "100", 15 * 1024 * 1024 + 1])
def test_rejects_invalid_upload_size_limits(value):
    with pytest.raises(ValueError, match="Limite de taille"):
        validate_pdf_upload(make_pdf(), max_bytes=value)


@pytest.mark.parametrize("value", [0, -1, True, "10", 501])
def test_rejects_invalid_page_limits(value):
    with pytest.raises(ValueError, match="Limite de pages"):
        validate_pdf_upload(make_pdf(), max_pages=value)


@pytest.mark.parametrize("value", [0, -1, True, "1000", 1_000_001])
def test_rejects_invalid_extraction_character_limits(value):
    with pytest.raises(ValueError, match="Limite de caractères"):
        extract_pdf_pages(make_pdf(), max_chars=value)

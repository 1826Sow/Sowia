"""Tests for PDF extraction safeguards."""
from io import BytesIO

import pytest
from pypdf import PdfWriter

from documents import extract_pdf_text


def test_blank_pdf_reports_that_no_text_was_found():
    output = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    writer.write(output)
    output.seek(0)

    with pytest.raises(ValueError, match="Aucun texte extractible"):
        extract_pdf_text(output)

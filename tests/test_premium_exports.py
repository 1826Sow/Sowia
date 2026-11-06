"""Tests for the Premium professional PDF export builder."""
from io import BytesIO

import pytest
from pypdf import PdfReader

from premium_exports import build_professional_pdf


def test_professional_export_creates_readable_paginated_pdf():
    payload = build_professional_pdf("Rapport de test", "Première section\n\nDeuxième section")
    assert payload.startswith(b"%PDF-")
    reader = PdfReader(BytesIO(payload))
    assert len(reader.pages) == 1
    extracted = reader.pages[0].extract_text()
    assert "Rapport de test" in extracted
    assert "Première section" in extracted
    assert "SOW IA" in extracted


@pytest.mark.parametrize(
    "title,content",
    [("", "Texte"), ("Titre", ""), (" " , "Texte")],
)
def test_professional_export_rejects_missing_title_or_content(title, content):
    with pytest.raises(ValueError):
        build_professional_pdf(title, content)


def test_professional_export_rejects_oversized_content():
    with pytest.raises(ValueError, match="longueur"):
        build_professional_pdf("Rapport", "x" * 150001)

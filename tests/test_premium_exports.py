"""Tests for the Premium professional PDF export builder and gate."""
from io import BytesIO
import pytest
from pypdf import PdfReader
from premium_exports import build_professional_pdf, create_premium_professional_pdf

def test_professional_export_creates_cover_and_readable_report():
    payload=build_professional_pdf("Rapport de test","Première section\\n\\nDeuxième section")
    reader=PdfReader(BytesIO(payload))
    assert payload.startswith(b"%PDF-") and len(reader.pages)==2
    assert "Rapport de test" in reader.pages[0].extract_text()
    assert "Première section" in reader.pages[1].extract_text()

def test_professional_export_requires_entitlement_before_build(monkeypatch):
    import premium_exports
    calls=[]
    monkeypatch.setattr(premium_exports,"require_feature_access",lambda c,u,f:calls.append((c,u,f)))
    payload=create_premium_professional_pdf("client","user","Titre","Texte")
    assert payload.startswith(b"%PDF-")
    assert calls==[("client","user","advanced_professional_exports")]

def test_professional_export_denies_before_build(monkeypatch):
    import premium_exports
    monkeypatch.setattr(premium_exports,"require_feature_access",lambda *a,**k:(_ for _ in ()).throw(PermissionError("Premium requis")))
    with pytest.raises(PermissionError): create_premium_professional_pdf("c","u","Titre","Texte")

@pytest.mark.parametrize("title,content",[("","Texte"),("Titre","")])
def test_professional_export_rejects_missing_content(title,content):
    with pytest.raises(ValueError): build_professional_pdf(title,content)

"""Tests for the Premium advanced PDF analysis gate."""
import pytest
import premium_analysis

def test_advanced_pdf_analysis_checks_entitlement_before_ai(monkeypatch):
    calls=[]
    def guard(client,user,feature): calls.append(("guard",client,user,feature))
    def answer(messages,**kwargs): calls.append(("answer",messages,kwargs)); return "Analyse structurée"
    monkeypatch.setattr(premium_analysis,"require_feature_access",guard)
    assert premium_analysis.analyze_pdf_advanced("client","user","Texte PDF",answer)=="Analyse structurée"
    assert calls[0]==("guard","client","user","advanced_pdf_analysis")
    assert calls[1][0]=="answer" and calls[1][2]["document_context"]=="Texte PDF"

def test_advanced_pdf_analysis_denies_before_calling_ai(monkeypatch):
    monkeypatch.setattr(premium_analysis,"require_feature_access",lambda *a,**k: (_ for _ in ()).throw(PermissionError("Premium requis")))
    with pytest.raises(PermissionError): premium_analysis.analyze_pdf_advanced("c","u","Texte",lambda *a,**k: pytest.fail("AI appelée sans Premium"))

def test_advanced_pdf_analysis_rejects_empty_document_before_entitlement(monkeypatch):
    monkeypatch.setattr(premium_analysis,"require_feature_access",lambda *a,**k: pytest.fail("Contrôle inutile"))
    with pytest.raises(ValueError): premium_analysis.analyze_pdf_advanced("c","u","",lambda *a,**k: "")

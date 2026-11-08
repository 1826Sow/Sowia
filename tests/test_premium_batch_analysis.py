"""Tests for Premium batch PDF analysis access and limits."""
from io import BytesIO
import pytest
from pypdf import PdfWriter
import premium_batch_analysis as batch

def test_batch_analysis_checks_entitlement_before_ai(monkeypatch):
    calls=[]
    monkeypatch.setattr(batch,"require_feature_access",lambda c,u,f:calls.append(("guard",c,u,f)))
    def answer(messages,**kwargs): calls.append(("answer",messages,kwargs)); return "Comparaison terminée"
    assert batch.analyze_pdf_batch("c","u",[("a.pdf","A"),("b.pdf","B")],answer)=="Comparaison terminée"
    assert calls[0]==("guard","c","u","batch_pdf_analysis")
    assert "DOCUMENT 1 — a.pdf" in calls[1][2]["document_context"]
    assert calls[1][2]["user_mode"]=="Professionnel"

def test_batch_analysis_denies_before_sending_text_to_ai(monkeypatch):
    monkeypatch.setattr(batch,"require_feature_access",lambda *a,**k: (_ for _ in ()).throw(PermissionError("Premium requis")))
    with pytest.raises(PermissionError): batch.analyze_pdf_batch("c","u",[("a.pdf","secret"),("b.pdf","secret")],lambda *a,**k: pytest.fail("AI appelée sans Premium"))

@pytest.mark.parametrize("docs",[[],[("a.pdf","A")],[(f"{i}.pdf","x") for i in range(6)]])
def test_batch_analysis_limits_document_count(docs):
    with pytest.raises(ValueError): batch.analyze_pdf_batch("c","u",docs,lambda *a,**k: "")

def test_batch_analysis_caps_total_context(monkeypatch):
    monkeypatch.setattr(batch,"require_feature_access",lambda *a,**k:None)
    received={}
    batch.analyze_pdf_batch("c","u",[(f"{i}.pdf","x"*7000) for i in range(5)],lambda m,**k:received.update(k) or "ok")
    assert len(received["document_context"]) <= batch.MAX_BATCH_TOTAL_CHARS+200

def pdf_bytes(count=1):
    buf=BytesIO(); writer=PdfWriter()
    for _ in range(count): writer.add_blank_page(width=72,height=72)
    writer.write(buf); return buf.getvalue()

class Upload:
    def __init__(self,name,payload): self.name=name; self.payload=payload; self.position=0
    def getvalue(self): return self.payload
    def seek(self,pos): self.position=pos

def test_batch_upload_validates_all_files_before_extracting():
    files=[Upload("ok.pdf",pdf_bytes()),Upload("bad.pdf",b"not a pdf")]
    calls=[]
    with pytest.raises(ValueError): batch.prepare_pdf_batch_uploads(files,lambda *a,**k:calls.append(1) or "text")
    assert calls==[]

def test_batch_upload_preparation_extracts_only_after_validation():
    files=[Upload("a.pdf",pdf_bytes()),Upload("b.pdf",pdf_bytes())]
    result=batch.prepare_pdf_batch_uploads(files,lambda f,max_chars:f.name)
    assert result==[("a.pdf","a.pdf"),("b.pdf","b.pdf")]

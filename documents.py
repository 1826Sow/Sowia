"""PDF text extraction helpers."""
from pypdf import PdfReader
def extract_pdf_text(uploaded_file,max_chars=100000):
    reader=PdfReader(uploaded_file); pages=[]; total=0
    for number,page in enumerate(reader.pages,start=1):
        chunk=f"\n--- Page {number} ---\n{page.extract_text() or ''}"; remaining=max_chars-total
        if remaining<=0: break
        pages.append(chunk[:remaining]); total+=len(chunk)
    result="".join(pages).strip()
    if not result: raise ValueError("Aucun texte extractible. Le PDF est peut-être scanné ou protégé.")
    return result

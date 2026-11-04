"""PDF text extraction helpers."""
from pypdf import PdfReader


def extract_pdf_text(uploaded_file, max_chars=100000):
    """Extract readable text while ignoring pages with no extractable text."""
    reader = PdfReader(uploaded_file)
    pages = []
    total = 0

    for number, page in enumerate(reader.pages, start=1):
        page_text = (page.extract_text() or "").strip()
        if not page_text:
            continue

        remaining = max_chars - total
        if remaining <= 0:
            break

        chunk = f"\n--- Page {number} ---\n{page_text}"
        pages.append(chunk[:remaining])
        total += min(len(chunk), remaining)

    result = "".join(pages).strip()
    if not result:
        raise ValueError(
            "Aucun texte extractible. Le PDF est peut-être scanné ou protégé."
        )
    return result

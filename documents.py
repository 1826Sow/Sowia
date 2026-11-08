"""PDF text extraction helpers."""
from pypdf import PdfReader


MAX_PDF_BYTES = 10 * 1024 * 1024
MAX_PDF_PAGES = 500


def _uploaded_size(uploaded_file):
    """Return a known upload size without consuming the file stream."""
    size = getattr(uploaded_file, "size", None)
    if size is not None:
        return int(size)
    getbuffer = getattr(uploaded_file, "getbuffer", None)
    if callable(getbuffer):
        return int(getbuffer().nbytes)
    return None


def extract_pdf_text(uploaded_file, max_chars=100000, max_pages=MAX_PDF_PAGES):
    """Extract readable text with upload, page-count, and output-size limits."""
    if not isinstance(max_chars, int) or isinstance(max_chars, bool) or max_chars < 1:
        raise ValueError("La limite de texte doit être un entier positif.")
    if not isinstance(max_pages, int) or isinstance(max_pages, bool) or max_pages < 1:
        raise ValueError("La limite de pages doit être un entier positif.")

    size = _uploaded_size(uploaded_file)
    if size is not None and size > MAX_PDF_BYTES:
        raise ValueError("Le PDF dépasse la limite de 10 Mo.")

    reader = PdfReader(uploaded_file)
    if reader.is_encrypted:
        raise ValueError("Ce PDF est protégé par mot de passe et ne peut pas être analysé.")
    if len(reader.pages) > max_pages:
        raise ValueError(f"Le PDF dépasse la limite de {max_pages} pages.")

    pages = []
    total = 0

    for number, page in enumerate(reader.pages, start=1):
        remaining = max_chars - total
        if remaining <= 0:
            break

        page_text = (page.extract_text() or "").strip()
        if not page_text:
            continue

        chunk = f"\n--- Page {number} ---\n{page_text}"
        pages.append(chunk[:remaining])
        total += min(len(chunk), remaining)

    result = "".join(pages).strip()
    if not result:
        raise ValueError(
            "Aucun texte extractible. Le PDF est peut-être scanné ou protégé."
        )
    return result

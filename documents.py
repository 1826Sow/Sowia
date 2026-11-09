"""PDF text extraction helpers, with OCR fallback for scanned documents."""
from io import BytesIO

from pypdf import PdfReader

MAX_PDF_BYTES = 10 * 1024 * 1024
MAX_PDF_PAGES = 500
MAX_OCR_PAGES = 30


def _uploaded_size(uploaded_file):
    """Return a known upload size without consuming the file stream."""
    size = getattr(uploaded_file, "size", None)
    if size is not None:
        return int(size)
    getbuffer = getattr(uploaded_file, "getbuffer", None)
    if callable(getbuffer):
        return int(getbuffer().nbytes)
    return None


def _ocr_pdf_pages(pdf_bytes, max_chars, max_pages):
    """Recognize scanned page images. OCR is deliberately page-limited."""
    try:
        import pypdfium2 as pdfium
        import pytesseract
    except ImportError as exc:
        raise ValueError(
            "Ce PDF semble être scanné. Le module OCR n'est pas encore installé."
        ) from exc

    pdf = pdfium.PdfDocument(pdf_bytes)
    pages = []
    total = 0
    page_limit = min(len(pdf), max_pages, MAX_OCR_PAGES)
    try:
        for index in range(page_limit):
            remaining = max_chars - total
            if remaining <= 0:
                break
            page = pdf[index]
            bitmap = page.render(scale=2)
            image = bitmap.to_pil()
            text = (pytesseract.image_to_string(image, lang="fra+eng") or "").strip()
            if text:
                chunk = f"\n--- Page {index + 1} (OCR) ---\n{text}"
                pages.append(chunk[:remaining])
                total += min(len(chunk), remaining)
            image.close()
            page.close()
    finally:
        pdf.close()
    return "".join(pages).strip()


def extract_pdf_text(uploaded_file, max_chars=100000, max_pages=MAX_PDF_PAGES):
    """Extract selectable PDF text, then use OCR when pages are scanned."""
    if not isinstance(max_chars, int) or isinstance(max_chars, bool) or max_chars < 1:
        raise ValueError("La limite de texte doit être un entier positif.")
    if not isinstance(max_pages, int) or isinstance(max_pages, bool) or max_pages < 1:
        raise ValueError("La limite de pages doit être un entier positif.")

    size = _uploaded_size(uploaded_file)
    if size is not None and size > MAX_PDF_BYTES:
        raise ValueError("Le PDF dépasse la limite de 10 Mo.")

    getvalue = getattr(uploaded_file, "getvalue", None)
    if callable(getvalue):
        pdf_bytes = getvalue()
    else:
        seek = getattr(uploaded_file, "seek", None)
        if callable(seek):
            seek(0)
        read = getattr(uploaded_file, "read", None)
        if not callable(read):
            raise ValueError("Le fichier PDF reçu ne peut pas être lu.")
        pdf_bytes = read()

    if not pdf_bytes or b"%PDF-" not in pdf_bytes[:1024]:
        raise ValueError("Le fichier sélectionné ne semble pas être un PDF valide.")

    reader = PdfReader(BytesIO(pdf_bytes), strict=False)
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
        if page_text:
            chunk = f"\n--- Page {number} ---\n{page_text}"
            pages.append(chunk[:remaining])
            total += min(len(chunk), remaining)

    result = "".join(pages).strip()
    if result:
        return result

    # No selectable text: treat the PDF as scanned and try OCR.
    try:
        result = _ocr_pdf_pages(pdf_bytes, max_chars, max_pages)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(
            "La lecture OCR de ce PDF a échoué. Le document est peut-être endommagé ou protégé."
        ) from exc

    if not result:
        raise ValueError(
            "Aucun texte extractible n'a été trouvé. Le PDF est peut-être vide, protégé ou constitué d'images trop floues."
        )
    return result

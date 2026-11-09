"""PDF text extraction helpers."""
from io import BytesIO

from pypdf import PdfReader


MAX_PDF_BYTES = 10 * 1024 * 1024
MAX_PDF_PAGES = 500
MAX_OCR_PAGES = 20


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

    # Streamlit's UploadedFile is a BytesIO object. Rebuild the stream
    # from its complete bytes so a previous read or mobile upload cannot
    # leave the PDF reader positioned at the end of the file.
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
        if not page_text:
            continue

        chunk = f"\n--- Page {number} ---\n{page_text}"
        pages.append(chunk[:remaining])
        total += min(len(chunk), remaining)

    result = "".join(pages).strip()
    if result:
        return result

    # Scanned PDFs contain page images rather than an embedded text layer.
    # Render a bounded number of pages and run local Tesseract OCR.
    if len(reader.pages) > MAX_OCR_PAGES:
        raise ValueError(
            "Ce PDF ne contient pas de texte sélectionnable et dépasse "
            f"la limite OCR de {MAX_OCR_PAGES} pages. Réduisez-le ou utilisez "
            "un PDF avec texte sélectionnable."
        )
    try:
        import fitz
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise ValueError(
            "Ce PDF semble être un scan. La lecture OCR n'est pas disponible "
            "sur cette version de SOW IA."
        ) from exc

    try:
        ocr_pages = []
        ocr_total = 0
        document = fitz.open(stream=pdf_bytes, filetype="pdf")
        try:
            for number, page in enumerate(document, start=1):
                remaining = max_chars - ocr_total
                if remaining <= 0:
                    break
                pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
                try:
                    page_text = pytesseract.image_to_string(image, lang="fra+eng").strip()
                except Exception:
                    page_text = pytesseract.image_to_string(image, lang="eng").strip()
                if page_text:
                    chunk = f"\n--- Page {number} (OCR) ---\n{page_text}"
                    ocr_pages.append(chunk[:remaining])
                    ocr_total += min(len(chunk), remaining)
        finally:
            document.close()
    except Exception as exc:
        raise ValueError(
            "La lecture OCR du PDF scanné a échoué. Vérifiez que le document "
            "n'est pas endommagé et réessayez."
        ) from exc

    ocr_result = "".join(ocr_pages).strip()
    if not ocr_result:
        raise ValueError(
            "Aucun texte n'a pu être reconnu dans ce scan. Vérifiez la netteté "
            "des pages et leur orientation."
        )
    return ocr_result

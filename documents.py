"""PDF text extraction helpers with bounded upload and parsing work."""
from io import BytesIO

from pypdf import PdfReader

MAX_PDF_BYTES = 10 * 1024 * 1024
MAX_PDF_PAGES = 200
MAX_EXTRACTED_CHARS = 100000


def extract_pdf_text(uploaded_file, max_chars=MAX_EXTRACTED_CHARS):
    """Extract readable text from a bounded, structurally valid PDF upload."""
    try:
        payload = uploaded_file.getvalue()
    except AttributeError:
        current_position = uploaded_file.tell()
        uploaded_file.seek(0, 2)
        size = uploaded_file.tell()
        uploaded_file.seek(current_position)
        if size > MAX_PDF_BYTES:
            raise ValueError("Le PDF dépasse la limite de 10 Mo.")
        uploaded_file.seek(0)
        payload = uploaded_file.read()
        uploaded_file.seek(0)

    if not payload:
        raise ValueError("Le fichier PDF est vide.")
    if len(payload) > MAX_PDF_BYTES:
        raise ValueError("Le PDF dépasse la limite de 10 Mo.")
    if not payload.startswith(b"%PDF-"):
        raise ValueError("Le contenu du fichier n'est pas un PDF valide.")

    try:
        reader = PdfReader(BytesIO(payload), strict=True)
        if reader.is_encrypted:
            raise ValueError("Les PDF protégés par mot de passe ne sont pas acceptés.")
        if len(reader.pages) < 1:
            raise ValueError("Le PDF ne contient aucune page.")
        if len(reader.pages) > MAX_PDF_PAGES:
            raise ValueError("Le PDF dépasse la limite de 200 pages.")
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("Le PDF est illisible ou mal formé.") from exc

    try:
        requested_limit = int(max_chars)
    except (TypeError, ValueError):
        raise ValueError("La limite d'extraction du PDF est invalide.")
    if requested_limit < 1:
        raise ValueError("La limite d'extraction du PDF doit être positive.")
    char_limit = min(requested_limit, MAX_EXTRACTED_CHARS)

    pages = []
    total = 0
    for number, page in enumerate(reader.pages, start=1):
        remaining = char_limit - total
        if remaining <= 0:
            break
        try:
            page_text = (page.extract_text() or "").strip()
        except Exception as exc:
            raise ValueError("Le texte du PDF n'a pas pu être extrait.") from exc
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

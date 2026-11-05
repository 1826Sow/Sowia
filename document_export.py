"""Bounded, injection-safe ZIP exports for the private document library."""
from io import BytesIO
import re
import zipfile

MAX_EXPORT_DOCUMENTS = 20
MAX_DOCUMENT_CHARS = 100_000
MAX_TOTAL_CHARS = 2_000_000


def _archive_name(filename):
    raw = str(filename or "").replace(chr(92), "/").split("/")[-1]
    stem = raw.rsplit(".", 1)[0] if "." in raw else raw
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", stem).strip("_-")[:70]
    return stem or "document"


def _metadata_value(value, fallback, limit):
    """Keep metadata on one line and remove non-printing control characters."""
    cleaned = " ".join(str(value or fallback).split())
    cleaned = "".join(char for char in cleaned if char.isprintable())
    return cleaned[:limit] or fallback


def build_documents_zip(
    documents,
    max_documents=MAX_EXPORT_DOCUMENTS,
    max_total_chars=MAX_TOTAL_CHARS,
):
    """Return a bounded ZIP of TXT exports; records must already be user-scoped."""
    if isinstance(max_documents, bool) or not isinstance(max_documents, int):
        raise ValueError("Limite de documents invalide.")
    if max_documents < 1 or max_documents > MAX_EXPORT_DOCUMENTS:
        raise ValueError("La limite d'export doit être comprise entre 1 et 20.")
    if isinstance(max_total_chars, bool) or not isinstance(max_total_chars, int):
        raise ValueError("Limite de taille invalide.")
    if max_total_chars < 1 or max_total_chars > MAX_TOTAL_CHARS:
        raise ValueError("La limite totale d'export est invalide.")

    items = list(documents or [])
    if not items:
        raise ValueError("Aucun document à exporter.")
    if len(items) > max_documents:
        raise ValueError("Trop de documents sélectionnés pour une seule archive.")

    output = BytesIO()
    used_names = set()
    total_chars = 0
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for item in items:
            if not isinstance(item, dict):
                continue
            text = str(item.get("extracted_text") or "").strip()
            if not text:
                continue
            if len(text) > MAX_DOCUMENT_CHARS:
                raise ValueError("Un document dépasse la limite de 100 000 caractères.")
            total_chars += len(text)
            if total_chars > max_total_chars:
                raise ValueError("L'archive dépasse la taille totale autorisée.")

            base = _archive_name(item.get("filename") or item.get("title"))
            candidate = f"{base}.txt"
            suffix = 2
            while candidate.casefold() in used_names:
                candidate = f"{base}_{suffix}.txt"
                suffix += 1
            used_names.add(candidate.casefold())
            metadata = [
                f"Titre : {_metadata_value(item.get('title'), 'Sans titre', 160)}",
                f"Catégorie : {_metadata_value(item.get('category'), 'Autres', 60)}",
                f"Dossier : {_metadata_value(item.get('folder'), 'Général', 60)}",
                f"Date : {_metadata_value(item.get('created_at'), 'Non renseignée', 80)}",
                "",
                text,
            ]
            archive.writestr(candidate, "\n".join(metadata))

    if not used_names:
        raise ValueError("Aucun texte exploitable à exporter.")
    return output.getvalue()

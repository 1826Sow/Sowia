"""Build ZIP archives from already user-scoped SOW IA documents."""
from io import BytesIO
import re
import zipfile


def _archive_name(filename):
    raw = str(filename or "").replace(chr(92), "/").split("/")[-1]
    stem = raw.rsplit(".", 1)[0] if "." in raw else raw
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", stem).strip("_-")[:70]
    return stem or "document"


def build_documents_zip(documents, max_documents=20):
    """Return a ZIP containing TXT exports; callers must pass user-scoped records."""
    items = list(documents or [])
    if not items:
        raise ValueError("Aucun document à exporter.")
    if len(items) > max_documents:
        raise ValueError("Trop de documents sélectionnés pour une seule archive.")
    output = BytesIO()
    used_names = set()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for index, item in enumerate(items, start=1):
            if not isinstance(item, dict) or not str(item.get("extracted_text") or "").strip():
                continue
            base = _archive_name(item.get("filename") or item.get("title"))
            candidate = f"{base}.txt"
            suffix = 2
            while candidate.casefold() in used_names:
                candidate = f"{base}_{suffix}.txt"
                suffix += 1
            used_names.add(candidate.casefold())
            metadata = [
                f"Titre : {str(item.get('title') or 'Sans titre')[:160]}",
                f"Catégorie : {str(item.get('category') or 'Autres')[:60]}",
                f"Dossier : {str(item.get('folder') or 'Général')[:60]}",
                f"Date : {str(item.get('created_at') or 'Non renseignée')[:80]}",
                "",
                str(item["extracted_text"]),
            ]
            archive.writestr(candidate, "\n".join(metadata))
    if not used_names:
        raise ValueError("Aucun texte exploitable à exporter.")
    return output.getvalue()

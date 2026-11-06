"""Private, user-scoped PDF storage using Supabase Storage."""
from io import BytesIO
import os
import re
from uuid import uuid4

from pypdf import PdfReader

BUCKET_NAME = "sowia-private-documents"
MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
PDF_SIGNATURE = b"%PDF-"


def _user_prefix(user):
    user_id = getattr(user, "id", None)
    if not user_id:
        raise PermissionError("Connexion requise.")
    return str(user_id)


def _safe_filename(filename):
    original = os.path.basename(str(filename or "").replace("\\", "/"))
    if not original.lower().endswith(".pdf"):
        raise ValueError("Seuls les fichiers PDF sont acceptés.")
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", original).strip("._")
    if not cleaned:
        raise ValueError("Nom de fichier invalide.")
    return cleaned[:100]


def _validate_pdf(payload):
    """Check both the PDF header and that a parser can read at least one page."""
    if not payload.startswith(PDF_SIGNATURE):
        raise ValueError("Le contenu du fichier n'est pas un PDF valide.")
    try:
        reader = PdfReader(BytesIO(payload), strict=True)
        if reader.is_encrypted:
            raise ValueError("Les PDF protégés par mot de passe ne sont pas acceptés.")
        if len(reader.pages) < 1:
            raise ValueError("Le PDF ne contient aucune page.")
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("Le contenu du fichier n'est pas un PDF valide ou lisible.") from exc


def _owned_path(user, path):
    prefix = _user_prefix(user) + "/"
    if not isinstance(path, str) or not path.startswith(prefix):
        raise PermissionError("Accès refusé à ce document.")
    relative = path[len(prefix):]
    if not relative or "/" in relative or ".." in relative:
        raise ValueError("Chemin de document invalide.")
    return path


def upload_document(client, user, filename, content):
    prefix = _user_prefix(user)
    safe_name = _safe_filename(filename)
    payload = bytes(content or b"")
    if not payload:
        raise ValueError("Le fichier PDF est vide.")
    if len(payload) > MAX_DOCUMENT_BYTES:
        raise ValueError("Le fichier dépasse la limite de 10 Mo.")
    _validate_pdf(payload)
    object_name = f"{uuid4().hex}_{safe_name}"
    path = f"{prefix}/{object_name}"
    client.storage.from_(BUCKET_NAME).upload(
        path,
        payload,
        file_options={"content-type": "application/pdf", "upsert": "false"},
    )
    return path


def list_documents(client, user):
    prefix = _user_prefix(user)
    return client.storage.from_(BUCKET_NAME).list(prefix)


def download_document(client, user, path):
    owned_path = _owned_path(user, path)
    return client.storage.from_(BUCKET_NAME).download(owned_path)


def delete_document(client, user, path):
    owned_path = _owned_path(user, path)
    return client.storage.from_(BUCKET_NAME).remove([owned_path])

"""Private, user-scoped PDF storage using Supabase Storage."""
from io import BytesIO
import os
import re
from uuid import uuid4

from pypdf import PdfReader

from feature_access import require_feature_access

BUCKET_NAME = "sowia-private-documents"
MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
MAX_DOCUMENT_PAGES = 200
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
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", original)
    stem = cleaned[:-4].strip("._")
    if not stem:
        stem = "document"
    # Keep the extension intact even when the original name is very long.
    return f"{stem[:96]}.pdf"


def _validate_pdf(payload):
    """Check PDF structure and bound page-processing work."""
    if not payload.startswith(PDF_SIGNATURE):
        raise ValueError("Le contenu du fichier n'est pas un PDF valide.")
    try:
        reader = PdfReader(BytesIO(payload), strict=True)
        if reader.is_encrypted:
            raise ValueError("Les PDF protégés par mot de passe ne sont pas acceptés.")
        page_count = len(reader.pages)
        if page_count < 1:
            raise ValueError("Le PDF ne contient aucune page.")
        if page_count > MAX_DOCUMENT_PAGES:
            raise ValueError("Le PDF dépasse la limite de 200 pages.")
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("Le contenu du fichier n'est pas un PDF valide ou lisible.") from exc


def _owned_path(user, path):
    prefix = _user_prefix(user) + "/"
    if not isinstance(path, str) or not path.startswith(prefix):
        raise PermissionError("Accès refusé à ce document.")
    relative = path[len(prefix):]
    if not relative or "/" in relative or "\\" in relative or ".." in relative or "\x00" in relative:
        raise ValueError("Chemin de document invalide.")
    return path


def upload_document(client, user, filename, content):
    prefix = _user_prefix(user)
    require_feature_access(client, user, "private_document_storage")
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
    require_feature_access(client, user, "private_document_storage")
    return client.storage.from_(BUCKET_NAME).list(prefix)


def download_document(client, user, path):
    owned_path = _owned_path(user, path)
    require_feature_access(client, user, "private_document_storage")
    return client.storage.from_(BUCKET_NAME).download(owned_path)


def delete_document(client, user, path):
    owned_path = _owned_path(user, path)
    require_feature_access(client, user, "private_document_storage")
    return client.storage.from_(BUCKET_NAME).remove([owned_path])

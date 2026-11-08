"""Private, user-scoped PDF storage using Supabase Storage."""
from io import BytesIO
from datetime import datetime, timezone
import os
import re

from pypdf import PdfReader
from uuid import uuid4

BUCKET_NAME = "sowia-files"
MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
MAX_DOCUMENT_PAGES = 500
PDF_SIGNATURE = b"%PDF-"
WORKSPACES = {"personal", "professional"}

def _user_prefix(user):
    user_id = getattr(user, "id", None)
    if not user_id:
        raise PermissionError("Connexion requise.")
    return str(user_id)

def _workspace(workspace_id):
    value = str(workspace_id or "personal")
    if value not in WORKSPACES:
        raise ValueError("Espace de travail invalide.")
    return value

def _safe_filename(filename):
    original = os.path.basename(str(filename or "").replace("\\", "/"))
    if not original.lower().endswith(".pdf"):
        raise ValueError("Seuls les fichiers PDF sont acceptés.")
    stem = re.sub(r"[^A-Za-z0-9._-]", "_", original[:-4]).strip("._")
    if not stem:
        raise ValueError("Nom de fichier invalide.")
    return f"{stem[:96]}.pdf"

def _owned_path(user, path, workspace_id="personal"):
    prefix = _user_prefix(user) + "/"
    workspace = _workspace(workspace_id)
    if not isinstance(path, str) or not path.startswith(prefix):
        raise PermissionError("Accès refusé à ce document.")
    relative = path[len(prefix):]
    parts = relative.split("/")
    # Legacy flat files remain accessible only from the Personal workspace.
    legacy_personal = workspace == "personal" and len(parts) == 1
    workspace_file = len(parts) == 2 and parts[0] == workspace
    if not (legacy_personal or workspace_file) or not parts[-1] or ".." in parts[-1]:
        raise ValueError("Chemin de document invalide.")
    return path

def _validate_pdf(payload):
    """Reject fake, encrypted, empty, or excessively large PDFs before upload."""
    if PDF_SIGNATURE not in payload[:1024]:
        raise ValueError("Le contenu du fichier n'est pas un PDF valide.")
    try:
        reader = PdfReader(BytesIO(payload))
        if reader.is_encrypted:
            raise ValueError("Les PDF protégés par mot de passe ne sont pas acceptés.")
        page_count = len(reader.pages)
        if page_count < 1:
            raise ValueError("Le PDF ne contient aucune page.")
        if page_count > MAX_DOCUMENT_PAGES:
            raise ValueError(f"Le PDF dépasse la limite de {MAX_DOCUMENT_PAGES} pages.")
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("Le contenu du fichier n'est pas un PDF valide ou lisible.") from exc

def upload_document(client, user, filename, content, workspace_id="personal"):
    prefix = _user_prefix(user)
    workspace = _workspace(workspace_id)
    safe_name = _safe_filename(filename)
    payload = bytes(content or b"")
    if not payload:
        raise ValueError("Le fichier PDF est vide.")
    if len(payload) > MAX_DOCUMENT_BYTES:
        raise ValueError("Le fichier dépasse la limite de 10 Mo.")
    _validate_pdf(payload)
    object_name = f"{uuid4().hex}_{safe_name}"
    path = f"{prefix}/{workspace}/{object_name}"
    client.storage.from_(BUCKET_NAME).upload(path, payload, file_options={"content-type": "application/pdf", "upsert": "false"})
    return path

def list_documents(client, user, workspace_id="personal"):
    prefix = _user_prefix(user)
    workspace = _workspace(workspace_id)
    bucket = client.storage.from_(BUCKET_NAME)
    documents = []
    if workspace == "personal":
        # Keep displaying old flat files as Personal documents.
        for item in bucket.list(prefix):
            name = item.get("name", "")
            if name.lower().endswith(".pdf"):
                documents.append({**item, "path": f"{prefix}/{name}"})
    for item in bucket.list(f"{prefix}/{workspace}"):
        name = item.get("name", "")
        if name.lower().endswith(".pdf"):
            documents.append({**item, "path": f"{prefix}/{workspace}/{name}"})
    return documents

def download_document(client, user, path, workspace_id="personal"):
    owned_path = _owned_path(user, path, workspace_id)
    return client.storage.from_(BUCKET_NAME).download(owned_path)

def delete_document(client, user, path, workspace_id="personal"):
    owned_path = _owned_path(user, path, workspace_id)
    return client.storage.from_(BUCKET_NAME).remove([owned_path])


def display_document_name(filename):
    """Hide the random storage identifier from a stored PDF's display name."""
    name = str(filename or "")
    prefix, separator, remainder = name.partition("_")
    if separator and len(prefix) == 32 and all(char in "0123456789abcdefABCDEF" for char in prefix):
        return remainder
    return name


def _document_created_timestamp(document):
    """Return a UTC timestamp for a Storage created_at value, or None."""
    value = document.get("created_at") if isinstance(document, dict) else None
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        created = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        return created.timestamp()
    except (TypeError, ValueError, OverflowError):
        return None


def filter_documents(documents, query="", sort_order="name_asc"):
    """Return a sorted, filtered copy without mutating the storage listing."""
    valid_orders = {"name_asc", "name_desc", "newest", "oldest"}
    if sort_order not in valid_orders:
        raise ValueError("Ordre de tri invalide.")
    search = str(query or "").strip().casefold()
    results = []
    for document in documents or []:
        if not isinstance(document, dict):
            continue
        name = str(document.get("name", "") or "")
        if not name:
            continue
        if search and search not in display_document_name(name).casefold():
            continue
        results.append(document)
    if sort_order in {"name_asc", "name_desc"}:
        return sorted(
            results,
            key=lambda item: display_document_name(item.get("name", "")).casefold(),
            reverse=(sort_order == "name_desc"),
        )

    dated = []
    undated = []
    for document in results:
        timestamp = _document_created_timestamp(document)
        if timestamp is None:
            undated.append(document)
        else:
            dated.append((timestamp, document))
    dated.sort(key=lambda pair: pair[0], reverse=(sort_order == "newest"))
    return [document for _, document in dated] + undated

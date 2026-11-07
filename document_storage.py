"""Private, user-scoped PDF storage using Supabase Storage."""
import os
import re
from uuid import uuid4

BUCKET_NAME = "sowia-private-documents"
MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
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
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", original).strip("._")
    if not cleaned:
        raise ValueError("Nom de fichier invalide.")
    # Keep the .pdf extension even when the original filename is very long.
    if len(cleaned) > 100:
        cleaned = cleaned[:-4][:96] + ".pdf"
    return cleaned


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


def upload_document(client, user, filename, content, workspace_id="personal"):
    prefix = _user_prefix(user)
    workspace = _workspace(workspace_id)
    safe_name = _safe_filename(filename)
    payload = bytes(content or b"")
    if not payload:
        raise ValueError("Le fichier PDF est vide.")
    if len(payload) > MAX_DOCUMENT_BYTES:
        raise ValueError("Le fichier dépasse la limite de 10 Mo.")
    object_name = f"{uuid4().hex}_{safe_name}"
    path = f"{prefix}/{workspace}/{object_name}"
    client.storage.from_(BUCKET_NAME).upload(
        path, payload,
        file_options={"content-type": "application/pdf", "upsert": "false"},
    )
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

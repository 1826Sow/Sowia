"""Persistent project register for the SOW IA Executive Hub.

All reads and writes are scoped to the authenticated owner and active workspace.
The database RLS policies remain the final authorization boundary.
"""
from datetime import datetime, timezone
from urllib.parse import urlsplit

WORKSPACES = {"personal", "professional"}
PROJECT_STATUSES = {"En cours", "À tester", "Validé", "Terminé"}
MAX_TITLE_LENGTH = 160
MAX_DESCRIPTION_LENGTH = 4000
MAX_DELIVERABLES = 100


def _owner_id(user):
    value = getattr(user, "id", None)
    if not value:
        raise PermissionError("Connexion requise.")
    return str(value)


def _workspace(workspace_id):
    value = str(workspace_id or "personal")
    if value not in WORKSPACES:
        raise ValueError("Espace de travail invalide.")
    return value


def _clean_text(value, field, maximum, required=False):
    cleaned = str(value or "").strip()
    if required and not cleaned:
        raise ValueError(f"{field} est obligatoire.")
    if len(cleaned) > maximum:
        raise ValueError(f"{field} dépasse {maximum} caractères.")
    return cleaned


def _validate_status(status):
    value = str(status or "En cours")
    if value not in PROJECT_STATUSES:
        raise ValueError("Statut de projet invalide.")
    return value


def _validate_deliverables(items):
    """Validate deliverable metadata before it reaches the JSONB column."""
    if not isinstance(items, list) or len(items) > MAX_DELIVERABLES:
        raise ValueError("Liste de livrables invalide (100 maximum).")
    for item in items:
        if isinstance(item, str):
            if len(item) > 2048:
                raise ValueError("Référence de livrable trop longue.")
            continue
        if not isinstance(item, dict):
            raise ValueError("Chaque livrable doit être un objet ou un libellé texte.")
        _clean_text(item.get("title"), "Le nom du livrable", 160, required=True)
        raw_url = item.get("url", "")
        if not isinstance(raw_url, str) or len(raw_url) > 2048:
            raise ValueError("Lien de livrable invalide.")
        if raw_url:
            if any(character.isspace() or ord(character) < 32 for character in raw_url):
                raise ValueError("Le lien du livrable contient des caractères interdits.")
            try:
                parsed = urlsplit(raw_url)
                hostname = parsed.hostname
                parsed.port  # Force validation of malformed port syntax.
            except ValueError as exc:
                raise ValueError("Lien HTTPS invalide.") from exc
            if (
                parsed.scheme.lower() != "https"
                or not hostname
                or parsed.username is not None
                or parsed.password is not None
            ):
                raise ValueError("Le lien du livrable doit être une URL HTTPS valide.")
    return items


def list_projects(client, user, workspace_id="personal", include_archived=False, limit=200):
    """Return only projects belonging to this user and workspace."""
    safe_limit = min(max(int(limit), 1), 500)
    query = (
        client.table("sowia_projects")
        .select("id, workspace_id, title, description, status, conversation_session_id, "
                "deliverables, metadata, archived_at, created_at, updated_at")
        .eq("user_id", _owner_id(user))
        .eq("workspace_id", _workspace(workspace_id))
    )
    if not include_archived:
        query = query.is_("archived_at", "null")
    return query.order("updated_at", desc=True).limit(safe_limit).execute().data or []


def create_project(client, user, title, description="", status="En cours",
                   workspace_id="personal", conversation_session_id=None,
                   deliverables=None, metadata=None):
    clean_title = _clean_text(title, "Le titre", MAX_TITLE_LENGTH, required=True)
    clean_description = _clean_text(description, "La description", MAX_DESCRIPTION_LENGTH)
    items = deliverables if deliverables is not None else []
    details = metadata if metadata is not None else {}
    items = _validate_deliverables(items)
    if not isinstance(details, dict):
        raise ValueError("Les métadonnées doivent être un objet.")
    payload = {
        "user_id": _owner_id(user),
        "workspace_id": _workspace(workspace_id),
        "title": clean_title,
        "description": clean_description,
        "status": _validate_status(status),
        "conversation_session_id": str(conversation_session_id).strip() if conversation_session_id else None,
        "deliverables": items,
        "metadata": details,
    }
    return client.table("sowia_projects").insert(payload).execute().data or []


def update_project(client, user, project_id, workspace_id="personal", **changes):
    allowed = {"title", "description", "status", "conversation_session_id", "deliverables", "metadata"}
    unknown = set(changes) - allowed
    if unknown:
        raise ValueError("Champ de projet non autorisé.")
    payload = {}
    if "title" in changes:
        payload["title"] = _clean_text(changes["title"], "Le titre", MAX_TITLE_LENGTH, required=True)
    if "description" in changes:
        payload["description"] = _clean_text(changes["description"], "La description", MAX_DESCRIPTION_LENGTH)
    if "status" in changes:
        payload["status"] = _validate_status(changes["status"])
    if "conversation_session_id" in changes:
        value = changes["conversation_session_id"]
        payload["conversation_session_id"] = str(value).strip() if value else None
    if "deliverables" in changes:
        value = changes["deliverables"]
        payload["deliverables"] = _validate_deliverables(value)
    if "metadata" in changes:
        value = changes["metadata"]
        if not isinstance(value, dict):
            raise ValueError("Les métadonnées doivent être un objet.")
        payload["metadata"] = value
    if not payload:
        raise ValueError("Aucune modification valide.")
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    return (
        client.table("sowia_projects").update(payload)
        .eq("id", project_id)
        .eq("user_id", _owner_id(user))
        .eq("workspace_id", _workspace(workspace_id))
        .execute().data or []
    )


def archive_project(client, user, project_id, workspace_id="personal"):
    """Soft-archive a project; never delete project or deliverable records."""
    now = datetime.now(timezone.utc).isoformat()
    return (
        client.table("sowia_projects")
        .update({"archived_at": now, "updated_at": now})
        .eq("id", project_id)
        .eq("user_id", _owner_id(user))
        .eq("workspace_id", _workspace(workspace_id))
        .is_("archived_at", "null")
        .execute().data or []
    )


def restore_project(client, user, project_id, workspace_id="personal"):
    """Restore a soft-archived project without changing its owner or workspace."""
    now = datetime.now(timezone.utc).isoformat()
    return (
        client.table("sowia_projects")
        .update({"archived_at": None, "updated_at": now})
        .eq("id", project_id)
        .eq("user_id", _owner_id(user))
        .eq("workspace_id", _workspace(workspace_id))
        .execute().data or []
    )

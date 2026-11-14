"""Persistent project register for the SOW IA Executive Hub.

All reads and writes are scoped to the authenticated owner and active workspace.
The database RLS policies remain the final authorization boundary.
"""
from datetime import datetime, timezone

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
    if not isinstance(items, list) or len(items) > MAX_DELIVERABLES:
        raise ValueError("Liste de livrables invalide (100 maximum).")
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
        if not isinstance(value, list) or len(value) > MAX_DELIVERABLES:
            raise ValueError("Liste de livrables invalide (100 maximum).")
        payload["deliverables"] = value
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

"""Authenticated, owner-scoped GDPR data export for SOW IA."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import base64

import document_storage

_MAX_DOCUMENT_EXPORT_BYTES = 50 * 1024 * 1024

_ALLOWED_WORKSPACES = {"personal", "professional"}
_PAGE_SIZE = 500

# Fixed allowlist: table names and columns are never user-controlled.
_EXPORT_TABLES = {
    "conversations": ("sowia_conversations", "id, session_id, title, created_at, updated_at"),
    "messages": ("sowia_messages", "id, session_id, role, content, created_at"),
    "memories": ("sowia_memory_items", "id, content, created_at, project_id"),
    "projects": ("sowia_projects", "id, title, description, status, conversation_session_id, deliverables, metadata, archived_at, created_at, updated_at"),
    "agents": ("sowia_agents", "id, project_id, name, description, can_read_workspace_memory, can_read_project_memory, can_write_private_memory, status, created_at, updated_at, enabled_tools"),
    "agent_memories": ("sowia_agent_memory_items", "id, agent_id, content, created_at, updated_at"),
    "agent_conversations": ("sowia_agent_conversations", "id, agent_id, title, created_at, updated_at"),
    "agent_messages": ("sowia_agent_messages", "id, conversation_id, agent_id, role, content, created_at"),
    "growth_leads": ("sowia_growth_leads", "id, organization, country, region, partner_type, website, source_url, notes, status, created_at, updated_at"),
    "preferences": ("sowia_user_preferences", "language, updated_at"),
}


def _owner_id(user):
    user_id = str(getattr(user, "id", "") or "").strip()
    if not user_id:
        raise PermissionError("Une connexion est nécessaire pour exporter vos données.")
    return user_id


def _workspace_id(value):
    workspace = str(value or "personal").strip().lower()
    if workspace not in _ALLOWED_WORKSPACES:
        raise ValueError("Espace de travail invalide.")
    return workspace


def _fetch_owned_rows(client, table_name, columns, owner_id, workspace):
    rows = []
    offset = 0
    while True:
        query = client.table(table_name).select(columns).eq("user_id", owner_id)
        if table_name != "sowia_user_preferences":
            query = query.eq("workspace_id", workspace)
        order_column = "updated_at" if table_name == "sowia_user_preferences" else "created_at"
        page = query.order(order_column, desc=False).range(
            offset, offset + _PAGE_SIZE - 1
        ).execute().data or []
        rows.extend(page)
        if len(page) < _PAGE_SIZE:
            break
        offset += _PAGE_SIZE
    return rows


def _list_private_pdf_objects(client, owner_id, workspace):
    """List PDFs in the owner's workspace with an explicit bounded page size."""
    bucket = client.storage.from_(document_storage.BUCKET_NAME)
    prefixes = [owner_id]
    if workspace == "personal":
        prefixes.append(owner_id + "/personal")
    else:
        prefixes = [owner_id + "/professional"]
    documents = []
    seen = set()
    for prefix in prefixes:
        items = bucket.list(prefix, {"limit": 1000, "offset": 0}) or []
        if len(items) >= 1000:
            raise RuntimeError("Votre espace contient au moins 1 000 fichiers. Export interrompu pour éviter un export incomplet.")
        for item in items:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "")
            if not name.lower().endswith(".pdf") or "/" in name or "\\\\" in name:
                continue
            path = prefix + "/" + name
            if path in seen:
                continue
            seen.add(path)
            documents.append({**item, "name": name, "path": path})
    return documents


def _export_private_documents(client, user, workspace):
    """Include only PDFs listed under this authenticated owner's selected workspace."""
    documents = _list_private_pdf_objects(client, _owner_id(user), workspace)
    exported = []
    total_bytes = 0
    owner_prefix = _owner_id(user) + "/"
    for item in documents:
        path = item.get("path") if isinstance(item, dict) else None
        name = item.get("name") if isinstance(item, dict) else None
        if not isinstance(path, str) or not isinstance(name, str) or not name.lower().endswith(".pdf"):
            continue
        if not path.startswith(owner_prefix):
            raise PermissionError("Un document hors de votre compte a été détecté.")
        payload = bytes(document_storage.download_document(client, user, path, workspace))
        if not payload or b"%PDF-" not in payload[:1024]:
            raise RuntimeError("Un document stocké n'est pas un PDF lisible.")
        if len(payload) > document_storage.MAX_DOCUMENT_BYTES:
            raise RuntimeError("Un document dépasse la limite autorisée de 10 Mo.")
        total_bytes += len(payload)
        if total_bytes > _MAX_DOCUMENT_EXPORT_BYTES:
            raise RuntimeError("Le volume total des PDF dépasse 50 Mo. Aucun export partiel n'a été préparé.")
        exported.append({
            "name": document_storage.display_document_name(name),
            "path": path,
            "created_at": item.get("created_at"),
            "content_type": "application/pdf",
            "size_bytes": len(payload),
            "content_base64": base64.b64encode(payload).decode("ascii"),
        })
    return exported


def build_personal_data_export(client, user, workspace_id="personal"):
    """Build a JSON-ready export for the authenticated owner, including private PDFs."""
    owner_id = _owner_id(user)
    workspace = _workspace_id(workspace_id)
    data = {
        key: _fetch_owned_rows(client, table, columns, owner_id, workspace)
        for key, (table, columns) in _EXPORT_TABLES.items()
    }
    data["private_documents"] = _export_private_documents(client, user, workspace)
    return {
        "format": "sowia-personal-data-export",
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "workspace": workspace,
        "profile": {
            "id": owner_id,
            "email": str(getattr(user, "email", "") or ""),
        },
        "data": data,
        "excluded": [
            "passwords_and_authentication_tokens",
            "api_keys_and_secrets",
            "payment_provider_credentials_and_webhook_payloads",
            "third_party_data_not_controlled_by_sow_ia",
        ],
    }


def serialize_personal_data_export(export_data):
    """Serialize an export as UTF-8 JSON suitable for a download button."""
    return json.dumps(
        export_data, ensure_ascii=False, indent=2, default=str
    ).encode("utf-8")

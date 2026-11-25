"""Authenticated, owner-scoped GDPR data export for SOW IA.

The exporter uses only the supplied authenticated Supabase client and explicit
user_id/workspace filters. It never requests credentials, tokens, payment
provider identifiers, webhook payloads, or storage objects.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json


_ALLOWED_WORKSPACES = {"personal", "professional"}
_PAGE_SIZE = 500

# Fixed allowlist: never accept table names or columns from user input.
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
        query = (client.table(table_name).select(columns)
            .eq("user_id", owner_id))
        if table_name != "sowia_user_preferences":
            query = query.eq("workspace_id", workspace)
        page = query.order("created_at", desc=False).range(
            offset, offset + _PAGE_SIZE - 1
        ).execute().data or []
        rows.extend(page)
        if len(page) < _PAGE_SIZE:
            break
        offset += _PAGE_SIZE
    return rows


def build_personal_data_export(client, user, workspace_id="personal"):
    """Return a JSON-ready export containing only this user's selected workspace."""
    owner_id = _owner_id(user)
    workspace = _workspace_id(workspace_id)
    data = {}
    for key, (table_name, columns) in _EXPORT_TABLES.items():
        data[key] = _fetch_owned_rows(
            client, table_name, columns, owner_id, workspace
        )

    # Do not expose auth tokens, provider IDs, password hashes, or payment secrets.
    profile = {
        "id": owner_id,
        "email": str(getattr(user, "email", "") or ""),
    }
    return {
        "format": "sowia-personal-data-export",
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "workspace": workspace,
        "profile": profile,
        "data": data,
        "excluded": [
            "passwords_and_authentication_tokens",
            "api_keys_and_secrets",
            "payment_provider_credentials_and_webhook_payloads",
            "private_storage_file_contents",
            "third_party_data_not_controlled_by_sow_ia",
        ],
    }


def serialize_personal_data_export(export_data):
    """Serialize an export as UTF-8 JSON suitable for a download button."""
    return json.dumps(
        export_data, ensure_ascii=False, indent=2, default=str
    ).encode("utf-8")

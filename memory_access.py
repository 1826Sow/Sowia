"""Authorized memory access for SOW IA developer tools and AI agents.

This is a server-side gateway: callers must pass the authenticated Supabase
client and the authenticated user object. Database ownership/RLS remains the
security boundary; this module never accepts a raw user_id from a caller.
"""
from __future__ import annotations

from memory_engine import build_agent_memory_context

_ALLOWED_WORKSPACES = {"personal", "professional"}


def load_developer_agent_memory(
    client,
    user,
    workspace_id="personal",
    project_id=None,
    query="",
    max_items=30,
    max_chars=12000,
):
    """Return relevant memory text for a developer or agent in one user scope.

    General workspace notes are always eligible. Project notes are eligible
    only when project_id names an active project owned by the authenticated
    user in the same workspace. Other projects and other users are excluded.

    The returned value contains memory content only (not internal metadata).
    It is suitable for adding to a server-side developer/agent prompt.
    """
    user_id = str(getattr(user, "id", "") or "").strip()
    if not user_id:
        raise PermissionError("An authenticated SOW IA user is required.")

    workspace = str(workspace_id or "personal").strip().lower()
    if workspace not in _ALLOWED_WORKSPACES:
        raise ValueError("Unknown SOW IA workspace.")

    selected_project_id = None
    if project_id not in (None, ""):
        try:
            selected_project_id = int(project_id)
        except (TypeError, ValueError) as exc:
            raise ValueError("Invalid project identifier.") from exc
        if selected_project_id <= 0:
            raise ValueError("Invalid project identifier.")

        owned_project = (
            client.table("sowia_projects")
            .select("id")
            .eq("id", selected_project_id)
            .eq("user_id", user_id)
            .eq("workspace_id", workspace)
            .is_("archived_at", "null")
            .limit(1)
            .execute()
            .data
            or []
        )
        if len(owned_project) != 1:
            raise PermissionError("The selected project is not available in this workspace.")

    # cloud_storage applies owner + workspace filters; Supabase RLS provides
    # the independent database-side enforcement.
    import cloud_storage

    records = cloud_storage.list_memories(client, user, workspace)
    scoped_records = [
        item for item in records
        if item.get("project_id") is None
        or (
            selected_project_id is not None
            and str(item.get("project_id")) == str(selected_project_id)
        )
    ]
    return build_agent_memory_context(
        scoped_records,
        query=query,
        max_items=max_items,
        max_chars=max_chars,
    )


def load_agent_memory_context(*args, **kwargs):
    """Agent-facing alias for the same owner/workspace/project-safe gateway."""
    return load_developer_agent_memory(*args, **kwargs)

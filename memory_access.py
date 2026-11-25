"""Authorized memory access for SOW IA developers and AI agents."""
from __future__ import annotations

from memory_engine import build_agent_memory_context

_ALLOWED_WORKSPACES = {"personal", "professional"}
_ALLOWED_AGENT_TOOLS = {"web_search", "memory_read", "memory_write"}
_DEFAULT_AGENT_TOOLS = {"memory_read", "memory_write"}


def _identity(user, workspace_id):
    user_id = str(getattr(user, "id", "") or "").strip()
    if not user_id:
        raise PermissionError("An authenticated SOW IA user is required.")
    workspace = str(workspace_id or "personal").strip().lower()
    if workspace not in _ALLOWED_WORKSPACES:
        raise ValueError("Unknown SOW IA workspace.")
    return user_id, workspace


def _owned_project(client, user_id, workspace, project_id):
    if project_id in (None, ""):
        return None
    try:
        selected = int(project_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid project identifier.") from exc
    if selected <= 0:
        raise ValueError("Invalid project identifier.")
    rows = (client.table("sowia_projects").select("id")
        .eq("id", selected).eq("user_id", user_id)
        .eq("workspace_id", workspace).is_("archived_at", "null")
        .limit(1).execute().data or [])
    if len(rows) != 1:
        raise PermissionError("The selected project is not available in this workspace.")
    return selected


def load_developer_agent_memory(
    client, user, workspace_id="personal", project_id=None,
    query="", max_items=30, max_chars=12000,
):
    """Developer context: general workspace notes plus the selected owned project."""
    user_id, workspace = _identity(user, workspace_id)
    selected_project_id = _owned_project(client, user_id, workspace, project_id)
    import cloud_storage
    records = cloud_storage.list_memories(client, user, workspace)
    scoped = [
        item for item in records
        if item.get("project_id") is None
        or (selected_project_id is not None
            and str(item.get("project_id")) == str(selected_project_id))
    ]
    return build_agent_memory_context(
        scoped, query=query, max_items=max_items, max_chars=max_chars
    )


def register_agent(
    client, user, name, workspace_id="personal", project_id=None,
    description="", can_read_workspace_memory=False,
    can_read_project_memory=False, can_write_private_memory=True,
    enabled_tools=None,
):
    """Create an owner-controlled agent with explicit memory permissions."""
    user_id, workspace = _identity(user, workspace_id)
    selected_project_id = _owned_project(client, user_id, workspace, project_id)
    clean_name = " ".join(str(name or "").split())[:120]
    clean_description = str(description or "").strip()[:2000]
    if not clean_name:
        raise ValueError("Agent name is required.")
    permissions = (
        can_read_workspace_memory, can_read_project_memory,
        can_write_private_memory,
    )
    if not all(isinstance(value, bool) for value in permissions):
        raise ValueError("Agent memory permissions must be boolean.")
    tools = set(_DEFAULT_AGENT_TOOLS if enabled_tools is None else enabled_tools)
    if not tools <= _ALLOWED_AGENT_TOOLS:
        raise ValueError("Agent tool selection contains an unsupported tool.")
    if "memory_write" in tools and not can_write_private_memory:
        raise ValueError("L'outil memory_write nécessite l'autorisation de mémoire privée.")
    rows = (client.table("sowia_agents").insert({
        "user_id": user_id,
        "workspace_id": workspace,
        "project_id": selected_project_id,
        "name": clean_name,
        "description": clean_description,
        "can_read_workspace_memory": can_read_workspace_memory,
        "can_read_project_memory": can_read_project_memory,
        "can_write_private_memory": can_write_private_memory,
        "enabled_tools": sorted(tools),
    }).select("id, name, workspace_id, project_id, status, can_read_workspace_memory, can_read_project_memory, can_write_private_memory, enabled_tools").execute().data or [])
    if len(rows) != 1:
        raise RuntimeError("SOW IA did not confirm agent creation.")
    return rows[0]


def list_agents(client, user, workspace_id="personal"):
    user_id, workspace = _identity(user, workspace_id)
    return (client.table("sowia_agents")
        .select("id, name, description, workspace_id, project_id, status, can_read_workspace_memory, can_read_project_memory, can_write_private_memory, enabled_tools")
        .eq("user_id", user_id).eq("workspace_id", workspace)
        .order("created_at", desc=True).limit(100).execute().data or [])


def add_agent_memory(client, user, agent_id, content, workspace_id="personal"):
    """Save a bounded note in one active agent's private memory."""
    user_id, workspace = _identity(user, workspace_id)
    cleaned = str(content or "").strip()
    if not cleaned or len(cleaned) > 4000:
        raise ValueError("Agent memory must contain 1 to 4,000 characters.")
    agent_rows = (client.table("sowia_agents")
        .select("id").eq("id", str(agent_id))
        .eq("user_id", user_id).eq("workspace_id", workspace)
        .eq("status", "active").eq("can_write_private_memory", True)
        .limit(1).execute().data or [])
    if len(agent_rows) != 1:
        raise PermissionError("This agent cannot write private memory.")
    return (client.table("sowia_agent_memory_items").insert({
        "agent_id": str(agent_id), "user_id": user_id,
        "workspace_id": workspace, "content": cleaned,
    }).select("id, content, created_at").execute().data or [])


def load_agent_memory_context(
    client, user, agent_id, workspace_id="personal",
    query="", max_items=30, max_chars=12000,
):
    """Build an agent prompt from private notes and explicitly granted shared notes."""
    user_id, workspace = _identity(user, workspace_id)
    agents = (client.table("sowia_agents")
        .select("id, project_id, can_read_workspace_memory, can_read_project_memory, status")
        .eq("id", str(agent_id)).eq("user_id", user_id)
        .eq("workspace_id", workspace).eq("status", "active")
        .limit(1).execute().data or [])
    if len(agents) != 1:
        raise PermissionError("Agent is not available to this authenticated user.")
    agent = agents[0]
    import cloud_storage
    records = (client.table("sowia_agent_memory_items")
        .select("content, created_at")
        .eq("agent_id", str(agent_id)).eq("user_id", user_id)
        .eq("workspace_id", workspace)
        .order("created_at", desc=True).limit(100).execute().data or [])
    authorized = list(records)
    if agent.get("can_read_workspace_memory") or agent.get("can_read_project_memory"):
        shared = cloud_storage.list_memories(client, user, workspace)
        project_id = agent.get("project_id")
        active_project_id = None
        if agent.get("can_read_project_memory") and project_id is not None:
            try:
                active_project_id = _owned_project(
                    client, user_id, workspace, project_id
                )
            except PermissionError:
                # A project may have been archived after agent registration.
                # Keep the agent's private memory usable, but share no project notes.
                active_project_id = None
        for item in shared:
            if item.get("project_id") is None and agent.get("can_read_workspace_memory"):
                authorized.append(item)
            elif (item.get("project_id") is not None
                  and active_project_id is not None
                  and str(item.get("project_id")) == str(active_project_id)):
                authorized.append(item)
    return build_agent_memory_context(
        authorized, query=query, max_items=max_items, max_chars=max_chars
    )


def update_agent_memory_permissions(
    client, user, agent_id, workspace_id="personal",
    can_read_workspace_memory=None, can_read_project_memory=None,
    can_write_private_memory=None,
):
    """Let the owner change only explicitly supplied boolean permissions."""
    user_id, workspace = _identity(user, workspace_id)
    changes = {}
    for key, value in (
        ("can_read_workspace_memory", can_read_workspace_memory),
        ("can_read_project_memory", can_read_project_memory),
        ("can_write_private_memory", can_write_private_memory),
    ):
        if value is not None:
            if not isinstance(value, bool):
                raise ValueError("Agent memory permissions must be boolean.")
            changes[key] = value
    if not changes:
        raise ValueError("At least one permission must be specified.")
    result = (client.table("sowia_agents").update(changes)
        .eq("id", str(agent_id)).eq("user_id", user_id)
        .eq("workspace_id", workspace).eq("status", "active")
        .execute().data or [])
    if not result:
        raise PermissionError("Agent is not available to this authenticated user.")
    return result



def update_agent_tools(client, user, agent_id, workspace_id="personal", enabled_tools=None):
    """Update an owner's active agent allowlist; never accept arbitrary tool names."""
    user_id, workspace = _identity(user, workspace_id)
    if not isinstance(enabled_tools, (list, tuple, set)):
        raise ValueError("Agent tools must be supplied as a list.")
    tools = set(enabled_tools)
    if not tools <= _ALLOWED_AGENT_TOOLS:
        raise ValueError("Agent tool selection contains an unsupported tool.")
    owned = (client.table("sowia_agents").select("can_write_private_memory")
        .eq("id", str(agent_id)).eq("user_id", user_id)
        .eq("workspace_id", workspace).eq("status", "active")
        .limit(1).execute().data or [])
    if len(owned) != 1:
        raise PermissionError("Agent is not available to this authenticated user.")
    if "memory_write" in tools and not owned[0].get("can_write_private_memory"):
        raise ValueError("L'outil memory_write nécessite l'autorisation de mémoire privée.")
    result = (client.table("sowia_agents").update({
        "enabled_tools": sorted(tools),
    }).eq("id", str(agent_id)).eq("user_id", user_id)
        .eq("workspace_id", workspace).eq("status", "active")
        .execute().data or [])
    if not result:
        raise PermissionError("Agent is not available to this authenticated user.")
    return result

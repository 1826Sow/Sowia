"""Quota-gated tools for owner-controlled persistent agent memory.

The memory_access module is supplied by the private-memory foundation PR.
Imports are lazy so this bridge remains importable while that dependency is
under review; actual memory calls require that foundation to be installed.
"""
from __future__ import annotations

from agent_runtime import execute_agent_action


class AgentMemoryToolError(ValueError):
    """Invalid persistent-memory tool request."""


def _workspace(value):
    workspace = str(value or "personal").strip().lower()
    if workspace not in {"personal", "professional"}:
        raise AgentMemoryToolError("Espace mémoire invalide.")
    return workspace


def _read_memory(client, user, agent_id, workspace_id, query, max_items, max_chars):
    from memory_access import load_agent_memory_context

    return load_agent_memory_context(
        client, user, agent_id, workspace_id=workspace_id, query=query,
        max_items=max_items, max_chars=max_chars,
    )


def _write_memory(client, user, agent_id, workspace_id, content):
    from memory_access import add_agent_memory

    return add_agent_memory(
        client, user, agent_id, content, workspace_id=workspace_id,
    )


def list_agent_memory_tools():
    """Return tool schemas, never database callables or internal credentials."""
    return [
        {
            "name": "memory_read",
            "description": "Lire la mémoire privée de cet agent et les notes explicitement autorisées.",
            "input_schema": {
                "type": "object", "required": ["query"],
                "properties": {
                    "query": {"type": "string", "maxLength": 500},
                    "max_items": {"type": "integer", "minimum": 1, "maximum": 30},
                    "max_chars": {"type": "integer", "minimum": 500, "maximum": 12000},
                },
                "additionalProperties": False,
            },
        },
        {
            "name": "memory_write",
            "description": "Enregistrer une note dans la mémoire privée de cet agent.",
            "input_schema": {
                "type": "object", "required": ["content"],
                "properties": {
                    "content": {"type": "string", "minLength": 1, "maxLength": 4000},
                },
                "additionalProperties": False,
            },
        },
    ]


def execute_registered_agent_memory_tool(
    user_client, user, tool_name, request_id, agent_id, workspace_id="personal",
    arguments=None,
):
    """Validate, debit and run one private-memory operation for an owned agent.

    Identity comes from the authenticated server session. `memory_access`
    independently verifies agent ownership, workspace, status and permissions.
    Each read/write is priced as a 2-credit `tool_execution` action; the server
    computes the price through the quota RPC, never from these arguments.
    """
    name = str(tool_name or "").strip().lower()
    args = arguments if isinstance(arguments, dict) else None
    if args is None:
        raise AgentMemoryToolError("Les paramètres mémoire doivent être un objet.")
    workspace = _workspace(workspace_id)
    if not str(agent_id or "").strip() or len(str(agent_id)) > 64:
        raise AgentMemoryToolError("Identifiant d'agent invalide.")

    if name == "memory_read":
        allowed = {"query", "max_items", "max_chars"}
        if set(args) - allowed or "query" not in args:
            raise AgentMemoryToolError("Paramètres de lecture mémoire invalides.")
        query = args["query"]
        max_items = args.get("max_items", 10)
        max_chars = args.get("max_chars", 6000)
        if not isinstance(query, str) or len(query) > 500:
            raise AgentMemoryToolError("La recherche mémoire est limitée à 500 caractères.")
        if isinstance(max_items, bool) or not isinstance(max_items, int) or not 1 <= max_items <= 30:
            raise AgentMemoryToolError("max_items doit être compris entre 1 et 30.")
        if isinstance(max_chars, bool) or not isinstance(max_chars, int) or not 500 <= max_chars <= 12000:
            raise AgentMemoryToolError("max_chars doit être compris entre 500 et 12 000.")
        handler = lambda: _read_memory(
            user_client, user, str(agent_id), workspace, query,
            max_items, max_chars,
        )
    elif name == "memory_write":
        if set(args) != {"content"}:
            raise AgentMemoryToolError("Paramètres d'écriture mémoire invalides.")
        content = args["content"]
        if not isinstance(content, str) or not content.strip() or len(content) > 4000:
            raise AgentMemoryToolError("La note doit contenir entre 1 et 4 000 caractères.")
        handler = lambda: _write_memory(
            user_client, user, str(agent_id), workspace, content.strip(),
        )
    else:
        raise AgentMemoryToolError("Outil mémoire inconnu ou non autorisé.")

    return execute_agent_action(
        user_client, user, "tool_execution", request_id, handler,
    )

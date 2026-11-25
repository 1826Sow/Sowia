"""Allowlisted server-side tools available to SOW IA agents.

Tool names and handlers are defined in this module, never by browser input.
Each invocation passes through the common quota gate before the handler runs.
"""
from __future__ import annotations

from agent_runtime import execute_agent_action


class AgentToolError(ValueError):
    """Invalid or unavailable agent tool request."""


def _web_search_handler(query: str, max_results: int = 5):
    """Run SOW IA's existing bounded web search and return a safe result shape."""
    from websearch import search_web

    results = search_web(query, max_results=max_results)
    if not isinstance(results, list):
        raise RuntimeError("Le moteur de recherche a renvoyé un format inattendu.")

    normalized = []
    for item in results[:max_results]:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or item.get("href") or "").strip()
        if not url.startswith(("https://", "http://")):
            continue
        normalized.append({
            "title": str(item.get("title") or "Résultat")[:240],
            "url": url[:2048],
            "content": str(item.get("content") or item.get("raw_content") or "")[:1600],
        })
    return normalized


# This registry is intentionally static. Future tools must be added by reviewed
# server code with a corresponding quota action and validation contract.
_TOOL_REGISTRY = {
    "web_search": {
        "action": "web_search",
        "handler": _web_search_handler,
        "required": {"query"},
        "optional": {"max_results"},
    },
}


def list_agent_tools():
    """Return public tool descriptions without exposing Python callables."""
    return [{
        "name": "web_search",
        "description": "Rechercher des informations publiques sur le Web.",
        "input_schema": {
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {"type": "string", "minLength": 1, "maxLength": 500},
                "max_results": {"type": "integer", "minimum": 1, "maximum": 10},
            },
            "additionalProperties": False,
        },
    }]


def execute_registered_agent_tool(
    user_client, user, tool_name: str, request_id: str, arguments: dict,
    *, agent_id=None, workspace_id="personal",
):
    """Validate, debit and execute one allowlisted agent tool.

    The caller cannot provide a handler, import path, action cost, or user ID.
    `user_client` and `user` must originate from the authenticated server session.
    """
    name = str(tool_name or "").strip().lower()
    definition = _TOOL_REGISTRY.get(name)
    if definition is None:
        raise AgentToolError("Outil agent inconnu ou non autorisé.")
    if not isinstance(arguments, dict):
        raise AgentToolError("Les paramètres de l'outil doivent être un objet.")

    allowed_keys = definition["required"] | definition["optional"]
    unknown_keys = set(arguments) - allowed_keys
    missing_keys = definition["required"] - set(arguments)
    if unknown_keys or missing_keys:
        raise AgentToolError("Les paramètres de l'outil sont incomplets ou non autorisés.")

    query = arguments.get("query")
    if not isinstance(query, str) or not query.strip() or len(query.strip()) > 500:
        raise AgentToolError("La recherche doit contenir entre 1 et 500 caractères.")
    max_results = arguments.get("max_results", 5)
    if isinstance(max_results, bool) or not isinstance(max_results, int) or not 1 <= max_results <= 10:
        raise AgentToolError("Le nombre de résultats doit être un entier de 1 à 10.")

    return execute_agent_action(
        user_client,
        user,
        definition["action"],
        request_id,
        definition["handler"],
        query.strip(),
        max_results=max_results,
        agent_id=agent_id,
        workspace_id=workspace_id,
        tool_name=name if agent_id is not None else None,
    )

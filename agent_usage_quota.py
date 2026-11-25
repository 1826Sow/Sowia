"""Persistent, idempotent monthly quota access for SOW IA agents.

This module calls authenticated Supabase RPCs. It never accepts a user ID from
the caller: Postgres derives ownership from auth.uid() in the user's JWT.
"""
from __future__ import annotations

import uuid

from sowia_economy import EconomyError, action_credit_cost

MONTHLY_AGENT_CREDIT_LIMIT = 1000


def _authenticated_user_id(user):
    user_id = str(getattr(user, "id", "") or "").strip()
    if not user_id:
        raise PermissionError("Connexion requise pour utiliser les agents IA.")
    return user_id


def _rpc_row(result):
    data = getattr(result, "data", None)
    if isinstance(data, list):
        return data[0] if data else None
    if isinstance(data, dict):
        return data
    return None


def get_agent_usage(user_client, user):
    """Return the authenticated account's current UTC-month quota snapshot."""
    _authenticated_user_id(user)
    if user_client is None:
        raise RuntimeError("Le service de quota des agents n'est pas configuré.")
    result = user_client.rpc("sowia_get_agent_usage", {}).execute()
    row = _rpc_row(result)
    if not isinstance(row, dict):
        raise RuntimeError("Le compteur de crédits n'a pas renvoyé de résultat.")
    return {
        "month_start": row.get("month_start"),
        "used_credits": int(row.get("used_credits", 0)),
        "monthly_limit": int(row.get("monthly_limit", MONTHLY_AGENT_CREDIT_LIMIT)),
        "remaining_credits": int(row.get("remaining_credits", 0)),
    }


def consume_agent_action(user_client, user, action, request_id, *, agent_id=None, workspace_id=None, tool_name=None):
    """Atomically consume an action's server-defined credit cost.

    Reuse the same UUID request_id when retrying a request. The database RPC
    guarantees idempotency and computes the cost itself; client-supplied credit
    amounts and user IDs are never trusted.
    """
    _authenticated_user_id(user)
    if user_client is None:
        raise RuntimeError("Le service de quota des agents n'est pas configuré.")
    normalized_action = str(action or "").strip().lower()
    # Validate locally for fast feedback; the database independently validates.
    expected_cost = action_credit_cost(normalized_action)
    try:
        normalized_request_id = str(uuid.UUID(str(request_id)))
    except (ValueError, TypeError, AttributeError):
        raise EconomyError("Identifiant de requête invalide : un UUID est requis.") from None
    if agent_id is not None:
        if workspace_id not in {"personal", "professional"}:
            raise EconomyError("Espace agent invalide.")
        if tool_name not in {"agent_chat", "web_search", "memory_read", "memory_write"}:
            raise EconomyError("Outil agent invalide.")
        rpc_name = "sowia_consume_agent_action_for_agent"
        rpc_args = {
            "p_request_id": normalized_request_id,
            "p_action": normalized_action,
            "p_agent_id": str(agent_id),
            "p_workspace_id": workspace_id,
            "p_tool_name": tool_name,
        }
    else:
        rpc_name = "sowia_consume_agent_credits"
        rpc_args = {
            "p_request_id": normalized_request_id,
            "p_action": normalized_action,
        }
    result = user_client.rpc(rpc_name, rpc_args).execute()
    row = _rpc_row(result)
    if not isinstance(row, dict) or "allowed" not in row:
        raise RuntimeError("Le service de quota n'a pas renvoyé de décision valide.")
    return {
        "allowed": bool(row["allowed"]),
        "action": normalized_action,
        "requested_credits": expected_cost,
        "used_credits": int(row.get("used_credits", 0)),
        "monthly_limit": int(row.get("monthly_limit", MONTHLY_AGENT_CREDIT_LIMIT)),
        "remaining_credits": int(row.get("remaining_credits", 0)),
        "reason": str(row.get("reason") or ""),
        "request_id": normalized_request_id,
    }


def finish_agent_action(user_client, user, request_id, agent_id, status, error_code=None):
    """Finalize one agent activity row without exposing prompt or tool output."""
    _authenticated_user_id(user)
    try:
        normalized_request_id = str(uuid.UUID(str(request_id)))
        normalized_agent_id = str(uuid.UUID(str(agent_id)))
    except (ValueError, TypeError, AttributeError):
        raise EconomyError("Identifiant de tâche invalide.") from None
    if status not in {"completed", "failed"}:
        raise EconomyError("Statut de tâche invalide.")
    result = user_client.rpc(
        "sowia_finish_agent_action_for_agent",
        {
            "p_request_id": normalized_request_id,
            "p_agent_id": normalized_agent_id,
            "p_status": status,
            "p_error_code": str(error_code or "")[:80] or None,
        },
    ).execute()
    data = getattr(result, "data", None)
    if data is False:
        raise RuntimeError("La clôture de l'activité agent n'a pas été confirmée.")
    return data


def get_agent_activity(user_client, user, agent_id, limit=20):
    """Return one owner's per-agent lifetime totals and recent tool activity."""
    _authenticated_user_id(user)
    try:
        normalized_agent_id = str(uuid.UUID(str(agent_id)))
    except (ValueError, TypeError, AttributeError):
        raise EconomyError("Identifiant d'agent invalide.") from None
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 50:
        raise EconomyError("La limite d'historique doit être comprise entre 1 et 50.")
    result = user_client.rpc(
        "sowia_get_agent_activity",
        {"p_agent_id": normalized_agent_id, "p_limit": limit},
    ).execute()
    data = getattr(result, "data", None)
    if not isinstance(data, list):
        raise RuntimeError("L'historique agent n'a pas renvoyé de résultat valide.")
    if not data:
        return {"total_credits": 0, "total_actions": 0, "events": []}
    first = data[0]
    return {
        "total_credits": int(first.get("total_credits") or 0),
        "total_actions": int(first.get("total_actions") or 0),
        "events": [row for row in data if row.get("request_id")],
    }

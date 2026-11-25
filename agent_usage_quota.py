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


def consume_agent_action(user_client, user, action, request_id):
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
    result = user_client.rpc(
        "sowia_consume_agent_credits",
        {
            "p_request_id": normalized_request_id,
            "p_action": normalized_action,
        },
    ).execute()
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

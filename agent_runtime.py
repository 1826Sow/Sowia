"""Common, server-side execution gate for SOW IA agent actions.

Every billable agent action must pass through this module before its handler
runs. The authenticated Supabase RPC is the authority for quota and idempotency;
this module never accepts a user ID or client-supplied credit amount.
"""
from __future__ import annotations

from collections.abc import Callable

from agent_usage_quota import consume_agent_action


class AgentQuotaExceeded(PermissionError):
    """Raised when an agent action is blocked by the account's monthly quota."""

    def __init__(self, usage: dict):
        self.usage = dict(usage)
        super().__init__(
            "Quota mensuel des agents IA atteint. "
            "Aucune facturation supplémentaire n'a été déclenchée."
        )


class AgentRequestAlreadyRecorded(PermissionError):
    """Raised when an idempotency key was already claimed by an earlier attempt."""

    def __init__(self, usage: dict):
        self.usage = dict(usage)
        super().__init__(
            "Cette requête a déjà été enregistrée. "
            "Son gestionnaire ne sera pas exécuté une seconde fois."
        )


def execute_agent_action(
    user_client,
    user,
    action: str,
    request_id: str,
    handler: Callable,
    /,
    *args,
    **kwargs,
):
    """Authorize and execute one server-registered agent action.

    The quota is atomically consumed before the handler starts, so concurrent
    requests cannot run beyond the account limit. A retry must reuse request_id;
    the database RPC makes that debit idempotent. A repeated request is rejected
    after the RPC reports 'already_recorded', preventing the handler from running
    twice even though the original debit is not repeated. An attempted action
    consumes its published credits even if its handler later raises an exception.

    `handler` must be selected by trusted server code, never by a client-provided
    import path or callable name. User identity and credit cost are derived by
    the authenticated server/database path, not supplied by the caller.
    """
    if not callable(handler):
        raise TypeError("Un gestionnaire d'action serveur est requis.")

    usage = consume_agent_action(user_client, user, action, request_id)
    if not usage["allowed"]:
        raise AgentQuotaExceeded(usage)
    if usage.get("reason") == "already_recorded":
        raise AgentRequestAlreadyRecorded(usage)

    result = handler(*args, **kwargs)
    return {"result": result, "usage": usage}

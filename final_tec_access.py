"""Fail-closed server-side authorization for the FINAL TEC investor view.

This helper deliberately uses the authenticated Supabase session's JWT through
an RPC. It never reads an email, URL parameter, local role flag, or service key
as proof of investor authorization.
"""
from __future__ import annotations

from typing import Any


def authorize_final_tec_investor_viewer(
    supabase_client: Any,
    authenticated_user: Any,
) -> bool:
    """Return True only when Supabase confirms an active FINAL TEC viewer grant.

    Any missing identity, unavailable client/RPC, malformed response, or
    exception denies access. The SQL function uses auth.uid() from the current
    authenticated session and checks project, role, status and expiry.
    """
    user_id = getattr(authenticated_user, "id", None)
    if not user_id or supabase_client is None:
        return False

    try:
        rpc = getattr(supabase_client, "rpc", None)
        if not callable(rpc):
            return False
        response = rpc("final_tec_can_view_published_metrics").execute()
        return getattr(response, "data", None) is True
    except Exception:
        # Fail closed without exposing tokens, database details or exceptions.
        return False

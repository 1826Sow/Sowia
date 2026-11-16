"""Authenticated client for the SOW IA one-time PayPal Edge Function."""
from __future__ import annotations

import requests

from settings import get_setting

TIMEOUT_SECONDS = 25
FUNCTION_NAME = "paypal-one-time"


def _access_token(supabase_client) -> str:
    response = supabase_client.auth.get_session()
    session = getattr(response, "session", response)
    token = getattr(session, "access_token", None)
    if not token:
        raise PermissionError("Votre session SOW IA a expiré. Reconnectez-vous.")
    return str(token)


def invoke(supabase_client, action: str, order_id: str | None = None) -> dict:
    if action not in {"create", "capture"}:
        raise ValueError("Action de paiement non autorisée.")
    project_url = str(get_setting("SUPABASE_URL", "") or "").strip().rstrip("/")
    anon_key = str(get_setting("SUPABASE_ANON_KEY", "") or "").strip()
    if not project_url.startswith("https://") or not anon_key:
        raise RuntimeError("La connexion Supabase n'est pas configurée.")
    payload = {"action": action}
    if action == "capture":
        if not order_id:
            raise ValueError("Identifiant de commande manquant.")
        payload["order_id"] = str(order_id)
    response = requests.post(
        f"{project_url}/functions/v1/{FUNCTION_NAME}",
        json=payload,
        headers={
            "Authorization": f"Bearer {_access_token(supabase_client)}",
            "apikey": anon_key,
            "Content-Type": "application/json",
        },
        timeout=TIMEOUT_SECONDS,
    )
    if not response.ok:
        raise RuntimeError(f"Validation PayPal impossible (HTTP {response.status_code}).")
    result = response.json()
    if not isinstance(result, dict):
        raise RuntimeError("Réponse de paiement invalide.")
    return result

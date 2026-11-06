"""Persistent Premium entitlements backed by Supabase.

Reads use the authenticated user's RLS-scoped client. Writes require a
server-only service-role client and are called only after PayPal capture
validation succeeds.
"""
from datetime import datetime, timezone

from settings import get_setting


def create_admin_client():
    url = str(get_setting("SUPABASE_URL", "") or "").strip()
    service_key = str(get_setting("SUPABASE_SERVICE_ROLE_KEY", "") or "").strip()
    if not url or not service_key:
        return None
    if not url.startswith("https://"):
        raise ValueError("SUPABASE_URL doit utiliser HTTPS.")
    from supabase import create_client
    return create_client(url, service_key)


def get_entitlement(user_client, user):
    user_id = getattr(user, "id", None)
    if not user_id:
        raise PermissionError("Connexion requise.")
    result = (
        user_client.table("sowia_entitlements")
        .select("status, provider, paypal_order_id, amount, currency, updated_at")
        .eq("user_id", str(user_id))
        .maybe_single()
        .execute()
    )
    data = getattr(result, "data", None)
    return data if data and data.get("status") == "active" else None


def grant_paypal_entitlement(admin_client, user_id, order_id, amount, currency):
    if admin_client is None:
        raise RuntimeError("Le stockage sécurisé des abonnements n'est pas configuré.")
    if not all((user_id, order_id, amount)) or currency != "EUR":
        raise ValueError("Informations de paiement Premium incomplètes.")
    payload = {
        "user_id": str(user_id),
        "status": "active",
        "provider": "paypal",
        "paypal_order_id": str(order_id),
        "amount": str(amount),
        "currency": currency,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    return (
        admin_client.table("sowia_entitlements")
        .upsert(payload, on_conflict="user_id")
        .execute()
        .data
    )

"""Persistent Premium entitlements backed by Supabase.

Reads use the authenticated user's RLS-scoped client. Writes require a
server-only service-role client and are called only after PayPal capture
validation succeeds.
"""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

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
        .select("status, provider, paypal_order_id, paypal_subscription_id, paypal_plan_id, paypal_status, current_period_end, last_payment_at, amount, currency, updated_at")
        .eq("user_id", str(user_id))
        .maybe_single()
        .execute()
    )
    data = getattr(result, "data", None)
    return data if data and data.get("status") == "active" else None


def grant_paypal_entitlement(admin_client, user_id, order_id, amount, currency):
    if admin_client is None:
        raise RuntimeError("Le stockage sécurisé des abonnements n'est pas configuré.")
    normalized_user_id = str(user_id or "").strip()
    normalized_order_id = str(order_id or "").strip()
    if not normalized_user_id or not normalized_order_id or amount is None:
        raise ValueError("Informations de paiement Premium incomplètes.")
    try:
        normalized_amount = Decimal(str(amount)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("Le montant Premium doit être un montant en euros valide.")
    if (
        not normalized_amount.is_finite()
        or normalized_amount <= 0
        or normalized_amount > Decimal("9999.99")
        or str(currency).upper() != "EUR"
    ):
        raise ValueError("Le montant Premium ou la devise ne sont pas valides.")
    payload = {
        "user_id": normalized_user_id,
        "status": "active",
        "provider": "paypal",
        "paypal_order_id": normalized_order_id,
        "amount": f"{normalized_amount:.2f}",
        "currency": "EUR",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    return (
        admin_client.table("sowia_entitlements")
        .upsert(payload, on_conflict="user_id")
        .execute()
        .data
    )


def require_workspace_access(workspace_id, user_client, user):
    """Require an active entitlement for the Professional workspace.

    The Personal workspace remains free. Professional access fails closed if
    the user is unauthenticated or the entitlement is missing/unreadable.
    """
    if str(workspace_id or "").strip().lower() != "professional":
        return None
    return require_active_entitlement(user_client, user)


def require_active_entitlement(user_client, user):
    """Fail closed before executing any Premium-only server-side operation.

    Call this guard inside the trusted server path of every paid feature.
    A missing, inactive, or unreadable entitlement must never grant access.
    """
    entitlement = get_entitlement(user_client, user)
    if entitlement is None:
        raise PermissionError("Un accès SOW IA Premium actif est nécessaire.")
    return entitlement

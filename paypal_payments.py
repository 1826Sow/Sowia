"""Server-side PayPal Orders v2 helpers for SOW IA.

Only call these functions from the trusted Streamlit server. Never expose the
PayPal client secret or access token to browser-side code.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
import re
from uuid import uuid4

import requests

from settings import get_setting

TIMEOUT_SECONDS = 20


def _setting(name: str, default: str = "") -> str:
    return str(get_setting(name, default) or "").strip()


def paypal_configuration():
    """Return checkout configuration only after an explicit server-side enable switch."""
    enabled = _setting("SOWIA_PAYMENTS_ENABLED", "false").lower() in {"1", "true", "yes"}
    if not enabled:
        return None
    client_id = _setting("PAYPAL_CLIENT_ID")
    client_secret = _setting("PAYPAL_CLIENT_SECRET")
    price = _setting("PAYPAL_PREMIUM_PRICE")
    currency = _setting("PAYPAL_CURRENCY", "EUR").upper()
    mode = _setting("PAYPAL_MODE", "sandbox").lower()
    return_url = _setting("PAYPAL_RETURN_URL")
    cancel_url = _setting("PAYPAL_CANCEL_URL")
    if not all((client_id, client_secret, price, return_url, cancel_url)):
        return None
    if mode not in {"sandbox", "live"}:
        raise ValueError("PAYPAL_MODE doit être 'sandbox' ou 'live'.")
    if currency != "EUR":
        raise ValueError("La devise SOW IA doit être EUR pour ce parcours.")
    try:
        raw_amount = Decimal(price)
        if not raw_amount.is_finite():
            raise ValueError
        amount = raw_amount.quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("PAYPAL_PREMIUM_PRICE doit être un montant en euros valide.") from None
    if raw_amount != amount:
        raise ValueError("PAYPAL_PREMIUM_PRICE ne peut pas comporter plus de deux décimales.")
    if amount <= 0 or amount > Decimal("9999.99"):
        raise ValueError("Le prix Premium doit être compris entre 0,01 € et 9 999,99 €.")
    if not return_url.startswith("https://") or not cancel_url.startswith("https://"):
        raise ValueError("Les URL de retour PayPal doivent utiliser HTTPS.")
    base_url = (
        "https://api-m.sandbox.paypal.com"
        if mode == "sandbox"
        else "https://api-m.paypal.com"
    )
    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "amount": f"{amount:.2f}",
        "currency": currency,
        "mode": mode,
        "return_url": return_url,
        "cancel_url": cancel_url,
        "base_url": base_url,
    }


def _access_token(config):
    response = requests.post(
        f"{config['base_url']}/v1/oauth2/token",
        auth=(config["client_id"], config["client_secret"]),
        data={"grant_type": "client_credentials"},
        headers={"Accept": "application/json"},
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    token = response.json().get("access_token")
    if not token:
        raise RuntimeError("PayPal n'a pas fourni de jeton d'accès.")
    return token


def create_premium_order(user_id: str):
    """Create a fixed-price EUR order tied to the authenticated SOW IA user."""
    config = paypal_configuration()
    if not config:
        raise RuntimeError("La configuration PayPal n'est pas encore complète.")
    if not user_id:
        raise PermissionError("Une connexion SOW IA est nécessaire.")
    token = _access_token(config)
    response = requests.post(
        f"{config['base_url']}/v2/checkout/orders",
        json={
            "intent": "CAPTURE",
            "purchase_units": [{
                "reference_id": "sowia-premium",
                "custom_id": str(user_id),
                "description": "Accès Premium SOW IA",
                "amount": {
                    "currency_code": config["currency"],
                    "value": config["amount"],
                },
            }],
            "payment_source": {
                "paypal": {
                    "experience_context": {
                        "return_url": config["return_url"],
                        "cancel_url": config["cancel_url"],
                        "user_action": "PAY_NOW",
                    }
                }
            },
        },
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "PayPal-Request-Id": str(uuid4()),
        },
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    order = response.json()
    approval_url = next(
        (item.get("href") for item in order.get("links", [])
         if item.get("rel") in {"approve", "payer-action"}),
        None,
    )
    if not order.get("id") or not approval_url:
        raise RuntimeError("PayPal n'a pas retourné le lien d'approbation.")
    return {"id": order["id"], "approval_url": approval_url}


def _validate_completed_capture(details, normalized_order_id, user_id, config):
    """Validate the settled capture embedded in a completed PayPal order."""
    units = details.get("purchase_units") or []
    if len(units) != 1:
        raise PermissionError("Commande PayPal non reconnue.")
    unit = units[0]
    amount = unit.get("amount") or {}
    captures = (unit.get("payments") or {}).get("captures") or []
    if (
        details.get("id") != normalized_order_id
        or details.get("status") != "COMPLETED"
        or unit.get("custom_id") != str(user_id)
        or unit.get("reference_id") != "sowia-premium"
        or amount.get("currency_code") != config["currency"]
        or amount.get("value") != config["amount"]
        or len(captures) != 1
        or not str(captures[0].get("id") or "").strip()
        or captures[0].get("status") != "COMPLETED"
        or (captures[0].get("amount") or {}).get("currency_code") != config["currency"]
        or (captures[0].get("amount") or {}).get("value") != config["amount"]
    ):
        raise PermissionError("La capture PayPal existante ne correspond pas à cet achat SOW IA.")
    return details


def capture_premium_order(order_id: str, user_id: str):
    """Capture only an order whose server-side details match this user and price."""
    config = paypal_configuration()
    if not config:
        raise RuntimeError("La configuration PayPal n'est pas encore complète.")
    if not order_id or not user_id:
        raise PermissionError("Commande ou utilisateur manquant.")
    normalized_order_id = str(order_id).strip()
    if not re.fullmatch(r"[A-Z0-9]{1,50}", normalized_order_id):
        raise PermissionError("Identifiant de commande PayPal invalide.")
    token = _access_token(config)
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    base = config["base_url"]
    details_response = requests.get(
        f"{base}/v2/checkout/orders/{normalized_order_id}",
        headers=headers,
        timeout=TIMEOUT_SECONDS,
    )
    details_response.raise_for_status()
    details = details_response.json()
    if details.get("id") != normalized_order_id:
        raise PermissionError("La commande PayPal retournée ne correspond pas à la demande.")
    units = details.get("purchase_units") or []
    if len(units) != 1:
        raise PermissionError("Commande PayPal non reconnue.")
    unit = units[0]
    amount = unit.get("amount") or {}
    if (
        unit.get("custom_id") != str(user_id)
        or unit.get("reference_id") != "sowia-premium"
        or amount.get("currency_code") != config["currency"]
        or amount.get("value") != config["amount"]
        or details.get("intent") != "CAPTURE"
        or details.get("status") not in {"APPROVED", "COMPLETED"}
    ):
        raise PermissionError("La commande PayPal ne correspond pas à cet achat SOW IA.")
    if details.get("status") == "COMPLETED":
        return _validate_completed_capture(details, normalized_order_id, user_id, config)
    capture_response = requests.post(
        f"{base}/v2/checkout/orders/{normalized_order_id}/capture",
        json={},
        headers={**headers, "PayPal-Request-Id": f"sowia-capture-{normalized_order_id}"},
        timeout=TIMEOUT_SECONDS,
    )
    capture_response.raise_for_status()
    result = capture_response.json()
    try:
        return _validate_completed_capture(result, normalized_order_id, user_id, config)
    except PermissionError as exc:
        raise RuntimeError("Les détails de la capture PayPal ne correspondent pas à l'achat Premium.") from exc


def sync_one_time_paypal_refunds(admin_client, user_id: str, days: int = 90, limit: int = 500):
    """Detect refunded one-time captures and move them to manual review.

    The ledger supplies the user-to-capture association. PayPal's capture
    status alone does not prove each refund's exact amount, so this function
    never creates a refund amount from the original capture gross.
    """
    from datetime import datetime, timedelta, timezone
    import financial_ledger

    config = paypal_configuration()
    if not config or config["mode"] != "sandbox":
        raise RuntimeError("La synchronisation des remboursements ponctuels est limitée à PayPal Sandbox.")
    normalized_user_id = str(user_id or "").strip()
    if not normalized_user_id or admin_client is None:
        raise PermissionError("Compte utilisateur ou stockage serveur manquant.")
    if not isinstance(days, int) or not 1 <= days <= 366:
        raise ValueError("La période doit être comprise entre 1 et 366 jours.")
    if not isinstance(limit, int) or not 1 <= limit <= 500:
        raise ValueError("La limite doit être comprise entre 1 et 500 captures.")

    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    result = (
        admin_client.table("sowia_financial_transactions")
        .select("provider_payment_id, paypal_order_id, occurred_at")
        .eq("user_id", normalized_user_id)
        .eq("provider", "paypal")
        .eq("transaction_type", "payment")
        .eq("status", "confirmed")
        .gte("occurred_at", since)
        .order("occurred_at", desc=True)
        .limit(limit)
        .execute()
    )
    rows = getattr(result, "data", None) or []
    token = _access_token(config)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    checked = 0
    detected = 0
    flagged = 0
    entitlements_revoked = 0
    missing_order_links = 0
    for row in rows:
        capture_id = str((row or {}).get("provider_payment_id") or "").strip()
        if not re.fullmatch(r"[A-Z0-9_-]{5,100}", capture_id):
            continue
        response = requests.get(
            f"{config['base_url']}/v2/payments/captures/{capture_id}",
            headers=headers,
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        capture = response.json()
        if str(capture.get("id") or "").strip() != capture_id:
            raise PermissionError("PayPal a retourné une capture différente de celle demandée.")
        checked += 1
        if str(capture.get("status") or "").upper() in {"PARTIALLY_REFUNDED", "REFUNDED"}:
            detected += 1
            amount = capture.get("amount") or {}
            gross = (
                (capture.get("seller_receivable_breakdown") or {}).get("gross_amount")
                or amount
            )
            financial_ledger.flag_paypal_refund_for_review(
                admin_client,
                user_id=normalized_user_id,
                transaction={
                    "id": capture_id,
                    "status": str(capture.get("status") or "").upper(),
                    "amount_with_breakdown": {"gross_amount": gross},
                    "time": capture.get("update_time") or capture.get("create_time"),
                },
            )
            flagged += 1
            order_id = str((row or {}).get("paypal_order_id") or "").strip()
            if order_id:
                revoked = (
                    admin_client.table("sowia_entitlements")
                    .update({"status": "inactive"})
                    .eq("user_id", normalized_user_id)
                    .eq("paypal_order_id", order_id)
                    .eq("status", "active")
                    .execute()
                )
                if getattr(revoked, "data", None):
                    entitlements_revoked += len(revoked.data)
            else:
                # Older ledger rows may predate the order-link migration.
                # Never guess which entitlement belongs to a capture.
                missing_order_links += 1
    return {
        "captures_checked": checked,
        "refunds_detected": detected,
        "refunds_flagged_for_manual_review": flagged,
        "entitlements_revoked": entitlements_revoked,
        "captures_missing_order_link": missing_order_links,
        "limit_reached": len(rows) >= limit,
    }


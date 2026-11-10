"""Server-only persistence helpers for confirmed financial provider events."""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import re


def record_paypal_capture(admin_client, *, user_id, order_id, capture, amount, currency):
    """Record a server-validated PayPal capture idempotently.

    Call only after paypal_payments.capture_premium_order has validated the
    completed order and capture directly against PayPal.
    """
    if admin_client is None:
        raise RuntimeError("Client d'administration Supabase indisponible.")
    user_id = str(user_id or "").strip()
    order_id = str(order_id or "").strip()
    capture_id = str((capture or {}).get("id") or "").strip()
    currency = str(currency or "").strip().upper()
    if not user_id or not re.fullmatch(r"[A-Z0-9]{1,50}", order_id):
        raise ValueError("Utilisateur ou commande PayPal invalide.")
    if not re.fullmatch(r"[A-Z0-9_-]{5,100}", capture_id):
        raise ValueError("Identifiant de capture PayPal invalide.")
    if currency != "EUR":
        raise ValueError("Seule la devise EUR est admise pour ce parcours PayPal.")
    try:
        value = Decimal(str(amount)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("Montant PayPal invalide.") from None
    if not value.is_finite() or value <= 0 or value > Decimal("9999.99"):
        raise ValueError("Montant PayPal hors limites.")

    payload = {
        "user_id": user_id,
        "provider": "paypal",
        "provider_payment_id": capture_id,
        "transaction_type": "payment",
        "status": "confirmed",
        "gross_amount": f"{value:.2f}",
        "gross_currency": "EUR",
        "reference_amount_eur": f"{value:.2f}",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
    }
    # The provider payment id is the capture id, not the order id.
    return (
        admin_client.table("sowia_financial_transactions")
        .upsert(payload, on_conflict="provider,provider_payment_id,transaction_type", ignore_duplicates=True)
        .execute()
        .data
    )

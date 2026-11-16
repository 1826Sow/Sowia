"""Stripe-hosted card checkout for SOW IA Premium.

Card details are collected by Stripe Checkout; SOW IA never handles raw card data.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from settings import get_setting

def _setting(name: str, default: str = "") -> str:
    return str(get_setting(name, default) or "").strip()

def stripe_configuration():
    enabled = _setting("SOWIA_STRIPE_ENABLED", "false").lower() in {"1", "true", "yes"}
    if not enabled:
        return None
    secret = _setting("STRIPE_SECRET_KEY")
    price_id = _setting("STRIPE_PREMIUM_PRICE_ID")
    success_url = _setting("STRIPE_SUCCESS_URL")
    cancel_url = _setting("STRIPE_CANCEL_URL")
    amount = _setting("STRIPE_PREMIUM_PRICE_EUR", "9.90")
    if not all((secret, price_id, success_url, cancel_url)):
        return None
    if not price_id.startswith("price_"):
        raise ValueError("STRIPE_PREMIUM_PRICE_ID doit être un identifiant Price Stripe.")
    if not success_url.startswith("https://") or not cancel_url.startswith("https://"):
        raise ValueError("Les URL de retour Stripe doivent utiliser HTTPS.")
    try:
        value = Decimal(amount).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        raise ValueError("STRIPE_PREMIUM_PRICE_EUR doit être un montant EUR valide.") from None
    if not value.is_finite() or value <= 0 or value > Decimal("9999.99"):
        raise ValueError("Le prix Stripe doit être compris entre 0,01 € et 9 999,99 €.")
    return {"secret_key": secret, "price_id": price_id, "success_url": success_url,
            "cancel_url": cancel_url, "amount": f"{value:.2f}", "currency": "EUR"}

def create_card_checkout(user_id: str):
    config = stripe_configuration()
    if not config:
        raise RuntimeError("Le paiement par carte Stripe n'est pas encore configuré.")
    if not user_id:
        raise PermissionError("Une connexion SOW IA est nécessaire.")
    import stripe
    session = stripe.checkout.Session.create(
        api_key=config["secret_key"],
        mode="payment",
        payment_method_types=["card"],
        line_items=[{"price": config["price_id"], "quantity": 1}],
        client_reference_id=str(user_id),
        metadata={"sowia_user_id": str(user_id), "sowia_product": "premium"},
        success_url=config["success_url"] + ("&" if "?" in config["success_url"] else "?") + "stripe_session_id={CHECKOUT_SESSION_ID}",
        cancel_url=config["cancel_url"],
    )
    if not session.get("id") or not session.get("url"):
        raise RuntimeError("Stripe n'a pas retourné de session Checkout valide.")
    return {"id": str(session["id"]), "url": str(session["url"])}

def retrieve_paid_checkout(session_id: str, user_id: str):
    config = stripe_configuration()
    if not config:
        raise RuntimeError("Le paiement par carte Stripe n'est pas encore configuré.")
    normalized_id = str(session_id or "").strip()
    if not normalized_id.startswith("cs_") or len(normalized_id) > 255 or not user_id:
        raise PermissionError("Session Stripe ou utilisateur invalide.")
    import stripe
    session = stripe.checkout.Session.retrieve(normalized_id, api_key=config["secret_key"])
    if (session.get("id") != normalized_id
        or session.get("mode") != "payment"
        or session.get("payment_status") != "paid"
        or str(session.get("client_reference_id") or "") != str(user_id)
        or str((session.get("metadata") or {}).get("sowia_user_id") or "") != str(user_id)
        or str((session.get("metadata") or {}).get("sowia_product") or "") != "premium"
        or str(session.get("currency") or "").lower() != "eur"
        or int(session.get("amount_total") or 0) != int(Decimal(config["amount"]) * 100)):
        raise PermissionError("Le paiement Stripe n'est pas confirmé pour ce compte SOW IA.")
    intent = session.get("payment_intent")
    intent_id = intent.get("id") if isinstance(intent, dict) else intent
    if not intent_id:
        raise PermissionError("Stripe n'a pas confirmé l'identifiant du paiement.")
    return {"session_id": normalized_id, "payment_intent_id": str(intent_id),
            "amount": config["amount"], "currency": "EUR"}

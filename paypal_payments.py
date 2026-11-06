""""Server-side PayPal Orders v2 helpers for SOW IA.

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


def payments_enabled() -> bool:
    """Return whether the owner has explicitly enabled PayPal checkout."""
    return _setting("SOWIA_PAYMENTS_ENABLED", "false").lower() in {"1", "true", "yes"}


def paypal_configuration():
    """Return checkout configuration only after an explicit enable switch."""
    # Payments stay completely inactive by default until the owner explicitly
    # enables them after the application is finished and verified.
    if not payments_enabled():
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
        amount = raw_amount.quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        raise ValueError("PAYPAL_PREMIUM_PRICE doit être un montant en euros valide.")
    if not raw_amount.is_finite() or raw_amount != amount or amount <= 0 or amount > Decimal("9999.99"):
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


def _validate_order_id(order_id):
    """Accept only PayPal order identifiers before placing them in API paths."""
    value = str(order_id or "")
    if not re.fullmatch(r"[A-Za-z0-9-]{1,64}", value):
        raise ValueError("Identifiant de commande PayPal invalide.")
    return value


def _validate_completed_capture(
    payload, config, expected_order_id=None, expected_user_id=None
):
    """Require the exact SOW IA order, owner, and completed configured capture."""
    if expected_order_id is not None and payload.get("id") != expected_order_id:
        raise PermissionError("La réponse PayPal ne correspond pas à la commande demandée.")
    units = payload.get("purchase_units") or []
    if len(units) != 1:
        raise PermissionError("La commande PayPal est absente ou ambiguë.")
    unit = units[0]
    if expected_user_id is not None and (
        unit.get("custom_id") != str(expected_user_id)
        or unit.get("reference_id") != "sowia-premium"
    ):
        raise PermissionError("La capture PayPal ne correspond pas à cet utilisateur SOW IA.")
    captures = (unit.get("payments") or {}).get("captures") or []
    if len(captures) != 1:
        raise PermissionError("La capture PayPal est absente ou ambiguë.")
    capture = captures[0]
    amount = capture.get("amount") or {}
    if (
        capture.get("status") != "COMPLETED"
        or amount.get("currency_code") != config["currency"]
        or amount.get("value") != config["amount"]
    ):
        raise PermissionError("Le montant réellement capturé ne correspond pas au prix Premium.")
    return payload


def capture_premium_order(order_id: str, user_id: str):
    """Capture only an order whose server-side details match this user and price."""
    config = paypal_configuration()
    if not config:
        raise RuntimeError("La configuration PayPal n'est pas encore complète.")
    if not user_id:
        raise PermissionError("Commande ou utilisateur manquant.")
    order_id = _validate_order_id(order_id)
    token = _access_token(config)
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    base = config["base_url"]
    details_response = requests.get(
        f"{base}/v2/checkout/orders/{order_id}",
        headers=headers,
        timeout=TIMEOUT_SECONDS,
    )
    details_response.raise_for_status()
    details = details_response.json()
    units = details.get("purchase_units") or []
    if details.get("id") != order_id or len(units) != 1:
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
        return _validate_completed_capture(\n            details, config, expected_order_id=order_id, expected_user_id=user_id\n        )
    capture_response = requests.post(
        f"{base}/v2/checkout/orders/{order_id}/capture",
        json={},
        headers={**headers, "PayPal-Request-Id": f"sowia-capture-{order_id}"},
        timeout=TIMEOUT_SECONDS,
    )
    capture_response.raise_for_status()
    result = capture_response.json()
    if result.get("status") != "COMPLETED":
        raise RuntimeError("PayPal n'a pas confirmé le paiement.")
    return _validate_completed_capture(\n        result, config, expected_order_id=order_id, expected_user_id=user_id\n    )

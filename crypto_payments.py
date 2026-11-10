"""Provider-neutral validation for crypto checkout notifications.

This module does not verify provider signatures, call a blockchain, persist events,
or grant Premium. A provider adapter must verify the webhook signature and map
its authenticated payload into this normalized shape before calling validate.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
import re


_ALLOWED_STATUSES = {"confirmed", "settled"}
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$")
_ASSET_RE = re.compile(r"^[A-Z0-9]{2,16}$")
_NETWORK_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,39}$")


def _decimal(value, field):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f"{field} doit être un montant numérique valide.")
    if not result.is_finite() or result <= 0:
        raise ValueError(f"{field} doit être strictement positif et fini.")
    return result


def validate_confirmed_crypto_payment(
    event: dict,
    *,
    expected_order_id: str,
    expected_user_id: str,
    expected_asset: str,
    expected_network: str,
    expected_amount: str,
    allowed_assets: set[str],
    allowed_networks: set[str],
):
    """Validate a normalized event after provider-specific signature verification.

    Exact payment is required. Underpayments and overpayments are rejected for
    manual reconciliation; no tolerance or implicit conversion is applied.
    """
    if not isinstance(event, dict):
        raise ValueError("Événement de paiement invalide.")
    if event.get("signature_verified") is not True:
        raise PermissionError("La signature du webhook n'a pas été vérifiée.")
    if event.get("status") not in _ALLOWED_STATUSES:
        raise PermissionError("Le paiement crypto n'est pas définitivement confirmé.")

    event_id = str(event.get("event_id") or "").strip()
    provider_payment_id = str(event.get("provider_payment_id") or "").strip()
    order_id = str(event.get("order_id") or "").strip()
    user_id = str(event.get("user_id") or "").strip()
    asset = str(event.get("asset") or "").strip().upper()
    network = str(event.get("network") or "").strip()

    if not _ID_RE.fullmatch(event_id) or not _ID_RE.fullmatch(provider_payment_id):
        raise ValueError("Identifiants d'événement ou de paiement invalides.")
    if order_id != str(expected_order_id) or user_id != str(expected_user_id):
        raise PermissionError("Le paiement ne correspond pas à cette commande ou à cet utilisateur.")
    if not _ASSET_RE.fullmatch(asset) or asset != str(expected_asset).upper():
        raise PermissionError("L'actif reçu ne correspond pas à l'actif attendu.")
    if not _NETWORK_RE.fullmatch(network) or network != str(expected_network):
        raise PermissionError("Le réseau reçu ne correspond pas au réseau attendu.")
    if asset not in {str(item).upper() for item in allowed_assets}:
        raise PermissionError("Cet actif n'est pas autorisé par la liste blanche.")
    if network not in {str(item) for item in allowed_networks}:
        raise PermissionError("Ce réseau n'est pas autorisé par la liste blanche.")

    expected = _decimal(expected_amount, "Montant attendu")
    received = _decimal(event.get("amount"), "Montant reçu")
    if received != expected:
        raise PermissionError("Le montant reçu diffère du montant attendu ; rapprochement manuel requis.")

    return {
        "event_id": event_id,
        "provider_payment_id": provider_payment_id,
        "order_id": order_id,
        "user_id": user_id,
        "asset": asset,
        "network": network,
        "amount": format(received, "f"),
        "status": "confirmed",
    }

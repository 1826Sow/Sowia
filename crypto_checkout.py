"""Provider-neutral preparation of crypto checkout orders.

This module validates a server-side order draft and a hosted checkout URL.
It does not call a payment provider, create a database record, or grant access.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import re
from urllib.parse import urlparse


_CODE_RE = re.compile(r"^[A-Z0-9]{2,16}$")
_NETWORK_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,39}$")
_PRODUCT_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,79}$")


def _positive_decimal(value, field: str, *, max_value: str = "999999999999.99") -> Decimal:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"{field} doit être numérique.") from None
    if not amount.is_finite() or amount <= 0 or amount > Decimal(max_value):
        raise ValueError(f"{field} doit être strictement positif et dans la limite autorisée.")
    return amount


def prepare_crypto_order(
    *,
    user_id: str,
    workspace_id: str,
    product_code: str,
    reference_amount_eur: str,
    asset_code: str,
    network_code: str,
    expected_asset_amount: str,
    provider: str,
    allowed_assets: set[str],
    allowed_networks: set[str],
    now: datetime | None = None,
    lifetime_minutes: int = 20,
) -> dict:
    """Build a validated pending-order payload; persist it server-side only."""
    user_id = str(user_id or "").strip()
    provider = str(provider or "").strip().lower()
    product_code = str(product_code or "").strip().lower()
    asset_code = str(asset_code or "").strip().upper()
    network_code = str(network_code or "").strip()

    if not user_id:
        raise PermissionError("Utilisateur authentifié obligatoire.")
    if workspace_id not in {"personal", "professional"}:
        raise ValueError("Espace de travail invalide.")
    if not _PRODUCT_RE.fullmatch(product_code):
        raise ValueError("Code produit invalide.")
    if not provider or len(provider) > 40:
        raise ValueError("Prestataire invalide.")
    if not _CODE_RE.fullmatch(asset_code) or asset_code not in {str(x).upper() for x in allowed_assets}:
        raise ValueError("Actif non autorisé.")
    if not _NETWORK_RE.fullmatch(network_code) or network_code not in set(allowed_networks):
        raise ValueError("Réseau non autorisé.")
    if isinstance(lifetime_minutes, bool) or not isinstance(lifetime_minutes, int) or not 5 <= lifetime_minutes <= 60:
        raise ValueError("La durée de validité doit être comprise entre 5 et 60 minutes.")

    eur = _positive_decimal(reference_amount_eur, "Montant EUR", max_value="999999.99")
    crypto = _positive_decimal(expected_asset_amount, "Montant crypto")
    if max(0, -crypto.as_tuple().exponent) > 12:
        raise ValueError("Le montant crypto dépasse la précision autorisée.")

    issued_at = now or datetime.now(timezone.utc)
    if issued_at.tzinfo is None or issued_at.utcoffset() is None:
        raise ValueError("La date doit inclure un fuseau horaire.")
    issued_at = issued_at.astimezone(timezone.utc)
    expires_at = issued_at + timedelta(minutes=lifetime_minutes)

    return {
        "user_id": user_id,
        "workspace_id": workspace_id,
        "product_code": product_code,
        "reference_amount_eur": f"{eur:.2f}",
        "asset_code": asset_code,
        "network_code": network_code,
        "expected_asset_amount": format(crypto, "f"),
        "provider": provider,
        "status": "pending",
        "expires_at": expires_at.isoformat(),
    }


def validate_hosted_checkout_url(url: str, *, allowed_hosts: set[str]) -> str:
    """Accept only HTTPS hosted-checkout URLs on an explicit hostname allowlist."""
    if not isinstance(url, str) or not url.strip():
        raise ValueError("Lien de paiement manquant.")
    parsed = urlparse(url.strip())
    host = (parsed.hostname or "").lower()
    allowed = {str(item).strip().lower() for item in allowed_hosts}
    if parsed.scheme != "https" or not host or host not in allowed:
        raise PermissionError("Le lien de paiement n'utilise pas un domaine HTTPS autorisé.")
    if parsed.username or parsed.password:
        raise ValueError("Les identifiants intégrés dans le lien sont interdits.")
    return url.strip()

"""Validation and normalization for externally sourced market observations.

This module deliberately does not fetch prices. A quote is usable only when its
provider, instrument, currency, timestamp and data status are explicit.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import math
from typing import Any, Mapping
from urllib.parse import urlparse


VALID_STATUSES = {"real_time", "delayed", "indicative", "unknown"}


@dataclass(frozen=True)
class MarketObservation:
    symbol: str
    name: str
    exchange: str
    asset_type: str
    price: float
    currency: str
    provider: str
    source_url: str | None
    observed_at: datetime
    status: str
    delay_minutes: int | None

    @property
    def is_verified_live(self) -> bool:
        """True only for an explicitly labelled real-time observation."""
        return self.status == "real_time"


def _required_text(raw: Mapping[str, Any], key: str, max_length: int = 120) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} doit être renseigné.")
    value = value.strip()
    if len(value) > max_length:
        raise ValueError(f"{key} dépasse la longueur autorisée.")
    return value


def normalize_market_observation(raw: Mapping[str, Any]) -> MarketObservation:
    """Validate one provider observation; never infer real-time status."""
    if not isinstance(raw, Mapping):
        raise ValueError("L'observation doit être un objet de données.")

    symbol = _required_text(raw, "symbol", 32).upper()
    name = _required_text(raw, "name", 160)
    exchange = _required_text(raw, "exchange", 80)
    asset_type = _required_text(raw, "asset_type", 40).lower()
    provider = _required_text(raw, "provider", 100)

    currency = _required_text(raw, "currency", 3).upper()
    if len(currency) != 3 or not currency.isalpha():
        raise ValueError("La devise doit être un code alphabétique ISO à 3 lettres.")

    try:
        price = float(raw.get("price"))
    except (TypeError, ValueError):
        raise ValueError("Le cours doit être numérique.") from None
    if not math.isfinite(price) or price < 0:
        raise ValueError("Le cours doit être un nombre fini positif ou nul.")

    timestamp_value = raw.get("observed_at")
    if not isinstance(timestamp_value, str) or not timestamp_value.strip():
        raise ValueError("L'horodatage observé est obligatoire.")
    try:
        observed_at = datetime.fromisoformat(timestamp_value.strip().replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("L'horodatage doit être au format ISO 8601.") from None
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise ValueError("L'horodatage doit inclure un fuseau horaire.")
    observed_at = observed_at.astimezone(timezone.utc)

    status = str(raw.get("status", "unknown")).strip().lower()
    if status not in VALID_STATUSES:
        raise ValueError("Statut de cotation non reconnu.")

    delay = raw.get("delay_minutes")
    if delay is not None:
        if isinstance(delay, bool) or not isinstance(delay, int) or delay < 0:
            raise ValueError("Le délai doit être un entier positif ou nul.")
    if status == "delayed" and delay is None:
        raise ValueError("Une cotation différée doit préciser son délai en minutes.")
    if status == "real_time" and delay not in (None, 0):
        raise ValueError("Une cotation temps réel ne peut pas déclarer de délai positif.")

    source_url = raw.get("source_url")
    if source_url not in (None, ""):
        if not isinstance(source_url, str):
            raise ValueError("L'URL source est invalide.")
        parsed = urlparse(source_url.strip())
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("La source doit être une URL HTTPS.")
        source_url = source_url.strip()
    else:
        source_url = None

    return MarketObservation(
        symbol=symbol,
        name=name,
        exchange=exchange,
        asset_type=asset_type,
        price=price,
        currency=currency,
        provider=provider,
        source_url=source_url,
        observed_at=observed_at,
        status=status,
        delay_minutes=delay,
    )

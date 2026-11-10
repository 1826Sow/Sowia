"""Transparent weather-to-sector risk screening; no forecasts are fetched.

Scores are screening indicators, not probability of loss, price forecasts or
investment advice. Exposure factors must be supplied and justified by the user.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import math
from typing import Any, Iterable, Mapping
from urllib.parse import urlparse

EVENT_TYPES = {
    "heat", "cold", "drought", "flood", "storm", "wildfire",
    "heavy_rain", "snow_ice", "wind", "other",
}
EVENT_STATES = {"observed", "forecast"}
IMPACT_DIRECTIONS = {"risk_increase", "potential_benefit", "mixed", "unknown"}


@dataclass(frozen=True)
class WeatherEvent:
    event_id: str
    phenomenon: str
    state: str
    region: str
    severity: int
    probability_pct: float | None
    starts_at: datetime
    ends_at: datetime | None
    source_name: str
    source_url: str
    issued_at: datetime


@dataclass(frozen=True)
class SectorExposure:
    sector: str
    region: str
    vulnerability: float
    direction: str
    rationale: str


@dataclass(frozen=True)
class SectorRisk:
    event_id: str
    phenomenon: str
    state: str
    region: str
    sector: str
    direction: str
    screening_score: float
    severity: int
    probability_pct: float | None
    rationale: str
    source_name: str
    source_url: str
    issued_at: datetime


def _text(raw: Mapping[str, Any], key: str, limit: int = 160) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > limit:
        raise ValueError(f"{key} doit être renseigné (maximum {limit} caractères).")
    return value.strip()


def _timestamp(value: Any, field: str, required: bool = True) -> datetime | None:
    if value is None and not required:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} doit être un horodatage ISO 8601.")
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"{field} doit être un horodatage ISO 8601.") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} doit inclure un fuseau horaire.")
    return parsed.astimezone(timezone.utc)


def normalize_weather_event(raw: Mapping[str, Any]) -> WeatherEvent:
    if not isinstance(raw, Mapping):
        raise ValueError("L'événement météo doit être un objet.")
    event_id = _text(raw, "event_id", 80)
    phenomenon = _text(raw, "phenomenon", 40).lower()
    if phenomenon not in EVENT_TYPES:
        raise ValueError("Phénomène météorologique non reconnu.")
    state = _text(raw, "state", 20).lower()
    if state not in EVENT_STATES:
        raise ValueError("L'état doit être observed ou forecast.")
    region = _text(raw, "region", 120)
    severity = raw.get("severity")
    if isinstance(severity, bool) or not isinstance(severity, int) or not 1 <= severity <= 5:
        raise ValueError("La sévérité doit être un entier de 1 à 5.")
    probability = raw.get("probability_pct")
    if state == "forecast":
        if isinstance(probability, bool) or not isinstance(probability, (int, float)) or not math.isfinite(probability) or not 0 <= probability <= 100:
            raise ValueError("Une prévision doit préciser une probabilité entre 0 et 100.")
        probability = float(probability)
    elif probability is not None:
        if isinstance(probability, bool) or not isinstance(probability, (int, float)) or not math.isfinite(probability) or not 0 <= probability <= 100:
            raise ValueError("La probabilité doit être comprise entre 0 et 100.")
        probability = float(probability)
    starts = _timestamp(raw.get("starts_at"), "starts_at")
    ends = _timestamp(raw.get("ends_at"), "ends_at", required=False)
    if ends is not None and ends < starts:
        raise ValueError("La fin de l'événement précède son début.")
    source_url = _text(raw, "source_url", 500)
    parsed_url = urlparse(source_url)
    if parsed_url.scheme != "https" or not parsed_url.netloc:
        raise ValueError("La source doit être une URL HTTPS.")
    return WeatherEvent(
        event_id=event_id, phenomenon=phenomenon, state=state, region=region,
        severity=severity, probability_pct=probability, starts_at=starts,
        ends_at=ends, source_name=_text(raw, "source_name", 120),
        source_url=source_url, issued_at=_timestamp(raw.get("issued_at"), "issued_at"),
    )


def normalize_sector_exposure(raw: Mapping[str, Any]) -> SectorExposure:
    if not isinstance(raw, Mapping):
        raise ValueError("L'exposition sectorielle doit être un objet.")
    sector = _text(raw, "sector", 100)
    region = _text(raw, "region", 120)
    vulnerability = raw.get("vulnerability")
    if isinstance(vulnerability, bool) or not isinstance(vulnerability, (int, float)) or not math.isfinite(vulnerability) or not 0 <= vulnerability <= 1:
        raise ValueError("La vulnérabilité doit être comprise entre 0 et 1.")
    direction = _text(raw, "direction", 30)
    if direction not in IMPACT_DIRECTIONS:
        raise ValueError("Direction d'impact non reconnue.")
    rationale = _text(raw, "rationale", 500)
    return SectorExposure(sector, region, float(vulnerability), direction, rationale)


def assess_weather_impacts(
    events: Iterable[WeatherEvent | Mapping[str, Any]],
    exposures: Iterable[SectorExposure | Mapping[str, Any]],
) -> tuple[SectorRisk, ...]:
    """Match exact regions or explicit '*' global exposures."""
    normalized_events = tuple(e if isinstance(e, WeatherEvent) else normalize_weather_event(e) for e in events)
    normalized_exposures = tuple(x if isinstance(x, SectorExposure) else normalize_sector_exposure(x) for x in exposures)
    results = []
    for event in normalized_events:
        for exposure in normalized_exposures:
            if exposure.region not in (event.region, "*"):
                continue
            probability_factor = (event.probability_pct / 100) if event.probability_pct is not None else 1.0
            score = round(event.severity / 5 * probability_factor * exposure.vulnerability * 100, 1)
            results.append(SectorRisk(
                event_id=event.event_id, phenomenon=event.phenomenon,
                state=event.state, region=event.region, sector=exposure.sector,
                direction=exposure.direction, screening_score=score,
                severity=event.severity, probability_pct=event.probability_pct,
                rationale=exposure.rationale, source_name=event.source_name,
                source_url=event.source_url, issued_at=event.issued_at,
            ))
    return tuple(sorted(results, key=lambda item: item.screening_score, reverse=True))

"""Evidence and provenance rules for FINAL TEC investor-facing indicators."""
from __future__ import annotations

from datetime import datetime
from typing import Any


ALLOWED_STATUSES = {"verified", "projected", "synthetic", "pending"}


class EvidenceValidationError(ValueError):
    """Raised when an investor-facing indicator lacks required provenance."""


def validate_indicator(record: dict[str, Any]) -> dict[str, Any]:
    """Validate provenance without treating projections or demos as measured facts."""
    if not isinstance(record, dict):
        raise EvidenceValidationError("L'indicateur doit être un objet.")

    status = record.get("status")
    if status not in ALLOWED_STATUSES:
        raise EvidenceValidationError("Statut d'indicateur inconnu.")

    normalized = dict(record)
    if status == "verified":
        required = ("source_url", "observed_at", "evidence_ref", "owner")
        missing = [key for key in required if not str(record.get(key) or "").strip()]
        if missing:
            raise EvidenceValidationError(
                "Un indicateur vérifié exige : " + ", ".join(missing)
            )
        source_url = str(record["source_url"]).strip()
        if not source_url.startswith("https://"):
            raise EvidenceValidationError("La source d'un indicateur vérifié doit être HTTPS.")
        try:
            datetime.fromisoformat(str(record["observed_at"]).replace("Z", "+00:00"))
        except ValueError as exc:
            raise EvidenceValidationError("Date d'observation ISO 8601 invalide.") from exc
    elif status == "projected":
        if not str(record.get("assumptions") or "").strip():
            raise EvidenceValidationError("Une projection doit documenter ses hypothèses.")
        if not str(record.get("horizon") or "").strip():
            raise EvidenceValidationError("Une projection doit préciser son horizon.")
    elif status == "synthetic":
        if not str(record.get("label") or "").strip():
            raise EvidenceValidationError("Une donnée synthétique doit être explicitement étiquetée.")

    normalized["display_status"] = {
        "verified": "Mesuré et vérifié",
        "projected": "Projection — hypothèses déclarées",
        "synthetic": "Démonstration fictive",
        "pending": "En attente de source",
    }[status]
    return normalized


def build_pending_register() -> list[dict[str, str]]:
    """Return indicators awaiting real source connections; no values are fabricated."""
    return [
        {
            "indicator": "Jalons techniques",
            "expected_source": "Livrables et validations de jalons",
            "status": "pending",
            "display_status": "En attente de source",
        },
        {
            "indicator": "Tests IA / Edge",
            "expected_source": "Rapports de benchmark reproductibles",
            "status": "pending",
            "display_status": "En attente de source",
        },
        {
            "indicator": "Latence et disponibilité",
            "expected_source": "Mesures horodatées sur ressources autorisées",
            "status": "pending",
            "display_status": "En attente de source",
        },
        {
            "indicator": "Coûts et budget",
            "expected_source": "Registre financier FINAL TEC",
            "status": "pending",
            "display_status": "En attente de source",
        },
        {
            "indicator": "Pilotes et partenariats",
            "expected_source": "Accord ou validation documentaire",
            "status": "pending",
            "display_status": "En attente de source",
        },
    ]

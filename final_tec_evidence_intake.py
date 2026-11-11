"""Safe staging of FINAL TEC evidence submissions.

This module validates and normalizes a proposed evidence record. It does not
write to Supabase, approve evidence, or publish investor-facing metrics.
"""
from __future__ import annotations

import math
import re
from datetime import datetime
from typing import Any
from urllib.parse import urlparse


ALLOWED_CATEGORIES = {
    "technical_milestones",
    "ai_edge_tests",
    "performance",
    "costs",
    "roadmap",
    "pilots_partnerships",
}
METRIC_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{1,79}$")
MAX_TEXT = 2000
ALLOWED_FIELDS = {
    "metric_key", "title", "category", "metric_value", "unit",
    "source_url", "observed_at", "evidence_ref", "evidence_owner",
    "assumptions", "horizon", "synthetic_label",
}


class EvidenceIntakeError(ValueError):
    """Raised when an evidence submission is malformed or unsafe."""


def _clean_text(value: Any, field: str, *, required: bool = False) -> str | None:
    if value is None or str(value).strip() == "":
        if required:
            raise EvidenceIntakeError(f"Champ obligatoire manquant : {field}.")
        return None
    if not isinstance(value, str):
        raise EvidenceIntakeError(f"Le champ {field} doit être du texte.")
    cleaned = value.strip()
    if len(cleaned) > MAX_TEXT:
        raise EvidenceIntakeError(f"Le champ {field} dépasse {MAX_TEXT} caractères.")
    return cleaned


def _validate_source_url(value: Any) -> str | None:
    url = _clean_text(value, "source_url")
    if url is None:
        return None
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise EvidenceIntakeError("La source doit être une URL HTTPS valide, sans identifiant intégré.")
    return url


def _validate_timestamp(value: Any) -> str | None:
    timestamp = _clean_text(value, "observed_at")
    if timestamp is None:
        return None
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceIntakeError("La date doit respecter le format ISO 8601.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise EvidenceIntakeError("La date doit inclure un fuseau horaire explicite.")
    return parsed.isoformat()


def _validate_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        if isinstance(value, str) and len(value) > MAX_TEXT:
            raise EvidenceIntakeError("La valeur textuelle est trop longue.")
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise EvidenceIntakeError("La valeur numérique doit être finie.")
        return value
    if isinstance(value, (dict, list)):
        # Restrict nested payloads to JSON-compatible scalar values and bound size.
        import json
        try:
            encoded = json.dumps(value, ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise EvidenceIntakeError("La valeur doit être sérialisable en JSON.") from exc
        if len(encoded) > MAX_TEXT:
            raise EvidenceIntakeError("La valeur structurée est trop volumineuse.")
        return value
    raise EvidenceIntakeError("Type de valeur non pris en charge.")


def prepare_evidence_submission(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a draft/pending row; client input can never self-approve or publish."""
    if not isinstance(payload, dict):
        raise EvidenceIntakeError("La soumission doit être un objet.")
    unknown = set(payload) - ALLOWED_FIELDS
    if unknown:
        raise EvidenceIntakeError("Champs non autorisés : " + ", ".join(sorted(unknown)))

    metric_key = _clean_text(payload.get("metric_key"), "metric_key", required=True)
    if not METRIC_KEY_RE.fullmatch(metric_key or ""):
        raise EvidenceIntakeError("Identifiant indicateur invalide.")

    title = _clean_text(payload.get("title"), "title", required=True)
    category = _clean_text(payload.get("category"), "category", required=True)
    if category not in ALLOWED_CATEGORIES:
        raise EvidenceIntakeError("Catégorie d'indicateur non autorisée.")

    owner = _clean_text(payload.get("evidence_owner"), "evidence_owner", required=True)
    record = {
        "project_key": "final-tec",
        "metric_key": metric_key,
        "title": title,
        "category": category,
        "metric_value": _validate_value(payload.get("metric_value")),
        "unit": _clean_text(payload.get("unit"), "unit"),
        "evidence_status": "pending",
        "source_url": _validate_source_url(payload.get("source_url")),
        "observed_at": _validate_timestamp(payload.get("observed_at")),
        "evidence_ref": _clean_text(payload.get("evidence_ref"), "evidence_ref"),
        "evidence_owner": owner,
        "assumptions": _clean_text(payload.get("assumptions"), "assumptions"),
        "horizon": _clean_text(payload.get("horizon"), "horizon"),
        "synthetic_label": _clean_text(payload.get("synthetic_label"), "synthetic_label"),
        "publication_state": "draft",
        "approved_by": None,
        "published_at": None,
    }
    return record

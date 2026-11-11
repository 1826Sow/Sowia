"""Controlled, side-effect-free review decisions for FINAL TEC evidence.

This module creates review decisions and audit events in memory only. It never
persists records, changes the source submission, or publishes investor metrics.
A successful decision means eligible for a separate publication workflow only.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import urlparse


class EvidenceReviewError(ValueError):
    """Raised when a review request violates the review policy."""


DECISIONS = {"approve_for_publication", "request_changes", "reject"}
REVIEWER_ROLES = {"final_tec_admin", "final_tec_analyst"}


def _aware_timestamp(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvidenceReviewError(f"{field} est obligatoire.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceReviewError(f"{field} doit respecter ISO 8601.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise EvidenceReviewError(f"{field} doit inclure un fuseau horaire.")
    return parsed.isoformat()


def _validate_verified_provenance(record: dict[str, Any]) -> None:
    required = ("source_url", "observed_at", "evidence_ref", "evidence_owner")
    missing = [key for key in required if not str(record.get(key) or "").strip()]
    if missing:
        raise EvidenceReviewError("Preuve incomplète : " + ", ".join(missing))
    parsed = urlparse(str(record["source_url"]).strip())
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise EvidenceReviewError("La source doit être une URL HTTPS valide.")
    _aware_timestamp(str(record["observed_at"]), "observed_at")


def build_evidence_review_decision(
    record: dict[str, Any],
    *,
    reviewer_id: str,
    reviewer_role: str,
    decision: str,
    rationale: str,
    reviewed_at: str,
) -> dict[str, Any]:
    """Validate reviewer authority and return an immutable-style decision event.

    The original record is not mutated. Approval only marks a dossier eligible
    for a later, separately authorized publication step.
    """
    if not isinstance(record, dict):
        raise EvidenceReviewError("La preuve à examiner doit être un objet.")
    if not isinstance(reviewer_id, str) or not reviewer_id.strip():
        raise EvidenceReviewError("Identifiant du réviseur obligatoire.")
    if reviewer_role not in REVIEWER_ROLES:
        raise EvidenceReviewError("Rôle non autorisé à examiner les preuves.")
    if reviewer_id.strip() == str(record.get("evidence_owner") or "").strip():
        raise EvidenceReviewError("Séparation des tâches : le déposant ne peut pas examiner sa propre preuve.")
    if decision not in DECISIONS:
        raise EvidenceReviewError("Décision inconnue.")
    if not isinstance(rationale, str) or len(rationale.strip()) < 10 or len(rationale) > 2000:
        raise EvidenceReviewError("Une justification de 10 à 2000 caractères est obligatoire.")
    if record.get("evidence_status") != "pending" or record.get("publication_state") != "draft":
        raise EvidenceReviewError("Seules les preuves en attente et en brouillon peuvent être examinées.")

    timestamp = _aware_timestamp(reviewed_at, "reviewed_at")
    if decision == "approve_for_publication":
        _validate_verified_provenance(record)

    resulting_status = {
        "approve_for_publication": "review_approved",
        "request_changes": "changes_requested",
        "reject": "rejected",
    }[decision]
    return {
        "event_type": "final_tec_evidence_review",
        "project_key": "final-tec",
        "metric_key": str(record.get("metric_key") or ""),
        "evidence_ref": str(record.get("evidence_ref") or ""),
        "reviewer_id": reviewer_id.strip(),
        "reviewer_role": reviewer_role,
        "decision": decision,
        "resulting_review_status": resulting_status,
        "rationale": rationale.strip(),
        "reviewed_at": timestamp,
        "publication_state": "draft",
        "published_at": None,
        "publication_authorized": False,
        "notice": "Décision de revue non persistée ; aucune publication n'a été effectuée.",
    }

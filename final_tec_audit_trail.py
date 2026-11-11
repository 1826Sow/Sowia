"""Append-only hash-chained audit events for FINAL TEC.

Pure in-memory primitives only: no database, filesystem, network, or publication.
A hash chain makes accidental/tampered changes detectable; it is not a substitute
for durable write-once storage, authenticated actors, signatures, or trusted time.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any


GENESIS_HASH = "0" * 64
ALLOWED_ACTIONS = {
    "evidence_submitted",
    "evidence_reviewed",
    "evidence_changes_requested",
    "evidence_rejected",
    "evidence_publication_requested",
    "evidence_published",
    "evidence_unpublished",
    "access_granted",
    "access_revoked",
}
ALLOWED_OUTCOMES = {"accepted", "denied", "pending", "completed", "failed"}
ALLOWED_ACTOR_ROLES = {
    "final_tec_admin",
    "final_tec_analyst",
    "final_tec_investor_viewer",
    "system",
}


class AuditTrailError(ValueError):
    """Raised for invalid audit events or a broken audit chain."""


def _timestamp(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AuditTrailError("Horodatage obligatoire.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AuditTrailError("Horodatage ISO 8601 invalide.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise AuditTrailError("L'horodatage doit inclure un fuseau horaire.")
    return parsed.isoformat()


def _canonical_hash(event: dict[str, Any]) -> str:
    payload = json.dumps(
        event, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def create_audit_event(
    *,
    actor_id: str,
    actor_role: str,
    action: str,
    resource_type: str,
    resource_id: str,
    outcome: str,
    occurred_at: str,
    reason_code: str,
    previous_hash: str = GENESIS_HASH,
) -> dict[str, Any]:
    """Create one validated event linked to the prior event hash."""
    fields = {
        "actor_id": actor_id,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "reason_code": reason_code,
    }
    for name, value in fields.items():
        if not isinstance(value, str) or not value.strip() or len(value) > 160:
            raise AuditTrailError(f"Champ invalide : {name}.")
    if actor_role not in ALLOWED_ACTOR_ROLES:
        raise AuditTrailError("Rôle d'acteur non autorisé.")
    if action not in ALLOWED_ACTIONS:
        raise AuditTrailError("Action d'audit inconnue.")
    if outcome not in ALLOWED_OUTCOMES:
        raise AuditTrailError("Résultat d'audit inconnu.")
    if not isinstance(previous_hash, str) or len(previous_hash) != 64:
        raise AuditTrailError("Hash précédent invalide.")
    try:
        int(previous_hash, 16)
    except ValueError as exc:
        raise AuditTrailError("Hash précédent invalide.") from exc

    event = {
        "schema_version": 1,
        "project_key": "final-tec",
        "actor_id": actor_id.strip(),
        "actor_role": actor_role,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "outcome": outcome,
        "occurred_at": _timestamp(occurred_at),
        "reason_code": reason_code,
        "previous_hash": previous_hash,
    }
    event["event_hash"] = _canonical_hash(event)
    return event


def append_audit_event(
    events: list[dict[str, Any]], event: dict[str, Any]
) -> list[dict[str, Any]]:
    """Return a new list with one event; never mutate the input list."""
    if not isinstance(events, list):
        raise AuditTrailError("Le journal doit être une liste.")
    if not verify_audit_chain(events):
        raise AuditTrailError("Le journal existant est invalide.")
    if not isinstance(event, dict):
        raise AuditTrailError("Événement invalide.")
    expected_previous = events[-1]["event_hash"] if events else GENESIS_HASH
    if event.get("previous_hash") != expected_previous:
        raise AuditTrailError("L'événement ne prolonge pas la chaîne existante.")
    if event.get("event_hash") != _canonical_hash({
        key: value for key, value in event.items() if key != "event_hash"
    }):
        raise AuditTrailError("Empreinte de l'événement invalide.")
    return [*events, dict(event)]


def verify_audit_chain(events: Any) -> bool:
    """Verify sequence links and event hashes; malformed input returns False."""
    if not isinstance(events, list):
        return False
    previous = GENESIS_HASH
    for event in events:
        if not isinstance(event, dict) or event.get("previous_hash") != previous:
            return False
        digest = event.get("event_hash")
        body = {key: value for key, value in event.items() if key != "event_hash"}
        try:
            calculated = _canonical_hash(body)
        except (TypeError, ValueError):
            return False
        if digest != calculated:
            return False
        previous = digest
    return True


def build_audit_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Return a minimal summary only after successful chain verification."""
    if not verify_audit_chain(events):
        raise AuditTrailError("Intégrité du journal non vérifiée.")
    actions: dict[str, int] = {}
    for event in events:
        action = event["action"]
        actions[action] = actions.get(action, 0) + 1
    return {
        "project_key": "final-tec",
        "event_count": len(events),
        "action_counts": dict(sorted(actions.items())),
        "integrity": "valid",
        "last_event_hash": events[-1]["event_hash"] if events else GENESIS_HASH,
        "storage_mode": "memory_only",
        "notice": "Chaîne vérifiée en mémoire ; aucune conservation durable ni preuve d'identité n'est fournie.",
    }

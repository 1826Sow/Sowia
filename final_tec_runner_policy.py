"""Offline fail-closed policy gate and state machine for FINAL TEC G0.

This module validates a proposed run manifest only. It never executes workloads,
contacts providers, opens network connections, provisions resources, or spends money.
"""
from __future__ import annotations

from datetime import datetime, timezone
import math
import re
from typing import Any, Mapping


class RunPolicyError(ValueError):
    """Raised when a run manifest or state transition violates policy."""


_STATES = {
    "draft": {"submitted", "rejected"},
    "submitted": {"authorized", "rejected"},
    "authorized": {"prepared", "rejected", "aborted"},
    "prepared": {"running", "rejected", "aborted", "timed_out"},
    "running": {"completed", "aborted", "timed_out", "budget_exceeded", "failed"},
    "completed": {"pending_review"},
    "pending_review": set(),
    "rejected": set(),
    "aborted": set(),
    "timed_out": set(),
    "budget_exceeded": set(),
    "failed": set(),
}

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/-]{1,119}$")
_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")


def _required_text(data: Mapping[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise RunPolicyError(f"Champ obligatoire absent ou invalide : {key}.")
    value = value.strip()
    if len(value) > 200 or not _ID_RE.fullmatch(value):
        raise RunPolicyError(f"Format invalide : {key}.")
    return value


def _positive_number(data: Mapping[str, Any], key: str, *, integer: bool = False) -> int | float:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RunPolicyError(f"{key} doit être numérique.")
    if integer and not isinstance(value, int):
        raise RunPolicyError(f"{key} doit être un entier.")
    if not math.isfinite(float(value)) or value <= 0:
        raise RunPolicyError(f"{key} doit être fini et strictement positif.")
    return value


def _utc_datetime(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise RunPolicyError(f"{field} est obligatoire.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RunPolicyError(f"{field} doit être une date ISO 8601.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise RunPolicyError(f"{field} doit inclure un fuseau horaire.")
    return parsed.astimezone(timezone.utc)


def validate_run_manifest(manifest: Mapping[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    """Return a normalized authorization summary or fail closed.

    The caller must still obtain independent authorization to execute anything.
    """
    if not isinstance(manifest, Mapping):
        raise RunPolicyError("Le manifeste doit être un objet.")
    required = {
        "run_id", "approval_ref", "operator_id", "resource_id",
        "authorization_status", "expires_at", "network_enabled",
        "budget_limit", "estimated_cost", "currency", "cost_basis",
        "max_duration_seconds", "max_requests", "max_repetitions",
        "max_cpu_cores", "max_memory_mb", "max_artifact_bytes",
        "emergency_stop",
    }
    missing = sorted(required - set(manifest))
    if missing:
        raise RunPolicyError("Manifeste incomplet : " + ", ".join(missing))
    allowed = required
    unknown = sorted(set(manifest) - allowed)
    if unknown:
        raise RunPolicyError("Champs non autorisés : " + ", ".join(unknown))

    run_id = _required_text(manifest, "run_id")
    approval_ref = _required_text(manifest, "approval_ref")
    operator_id = _required_text(manifest, "operator_id")
    resource_id = _required_text(manifest, "resource_id")

    if manifest["authorization_status"] != "approved":
        raise RunPolicyError("Autorisation explicite approuvée requise.")
    if manifest["network_enabled"] is not False:
        raise RunPolicyError("Le réseau doit être désactivé pour G0.")
    if manifest["emergency_stop"] is not False:
        raise RunPolicyError("Arrêt d'urgence actif : exécution refusée.")

    expires_at = _utc_datetime(manifest["expires_at"], "expires_at")
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None or current.utcoffset() is None:
        raise RunPolicyError("L'horloge de validation doit être timezone-aware.")
    if expires_at <= current.astimezone(timezone.utc):
        raise RunPolicyError("L'autorisation est expirée.")

    currency = manifest["currency"]
    if not isinstance(currency, str) or not _CURRENCY_RE.fullmatch(currency):
        raise RunPolicyError("Devise invalide : code ISO 4217 attendu.")
    cost_basis = _required_text(manifest, "cost_basis")

    budget = _positive_number(manifest, "budget_limit")
    estimate = _positive_number(manifest, "estimated_cost")
    if estimate > budget:
        raise RunPolicyError("Le coût estimé dépasse le budget plafond.")

    limits = {
        "max_duration_seconds": _positive_number(manifest, "max_duration_seconds", integer=True),
        "max_requests": _positive_number(manifest, "max_requests", integer=True),
        "max_repetitions": _positive_number(manifest, "max_repetitions", integer=True),
        "max_cpu_cores": _positive_number(manifest, "max_cpu_cores"),
        "max_memory_mb": _positive_number(manifest, "max_memory_mb", integer=True),
        "max_artifact_bytes": _positive_number(manifest, "max_artifact_bytes", integer=True),
    }
    if limits["max_duration_seconds"] > 86_400:
        raise RunPolicyError("Durée maximale G0 dépassée (24 heures).")
    if limits["max_requests"] > 1_000_000:
        raise RunPolicyError("Plafond G0 de requêtes dépassé.")
    if limits["max_repetitions"] > 10_000:
        raise RunPolicyError("Plafond G0 de répétitions dépassé.")
    if limits["max_cpu_cores"] > 64:
        raise RunPolicyError("Plafond G0 CPU dépassé.")
    if limits["max_memory_mb"] > 1_048_576:
        raise RunPolicyError("Plafond G0 mémoire dépassé.")
    if limits["max_artifact_bytes"] > 1_073_741_824:
        raise RunPolicyError("Plafond G0 artefacts dépassé.")

    return {
        "run_id": run_id,
        "approval_ref": approval_ref,
        "operator_id": operator_id,
        "resource_id": resource_id,
        "expires_at_utc": expires_at.isoformat(),
        "network_enabled": False,
        "budget_limit": float(budget),
        "estimated_cost": float(estimate),
        "currency": currency,
        "cost_basis": cost_basis,
        "limits": limits,
        "policy_result": "locally_validated_not_executed",
        "evidence_status": "pending",
        "publication_state": "draft",
    }


def transition_run_state(current: str, target: str, *, emergency_stop: bool = False) -> str:
    """Validate one explicit state transition; emergency stop always blocks progress."""
    if current not in _STATES or target not in _STATES:
        raise RunPolicyError("État inconnu.")
    if not isinstance(emergency_stop, bool):
        raise RunPolicyError("Le signal d'arrêt d'urgence doit être booléen.")
    if emergency_stop:
        if current in {"running", "prepared", "authorized"} and target == "aborted":
            return "aborted"
        raise RunPolicyError("Arrêt d'urgence actif : seule la transition vers aborted est permise.")
    if target not in _STATES[current]:
        raise RunPolicyError(f"Transition interdite : {current} -> {target}.")
    return target

"""Reproducible FINAL TEC benchmark intake and summary statistics.

Pure validation/calculation only: no remote execution, provider calls, database
writes, publication, or automatic verification.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime
from typing import Any


ALLOWED_RESOURCE_TYPES = {"cloud_gpu", "edge_device", "private_server", "cpu"}
ALLOWED_WORKLOADS = {"inference", "embedding", "batch", "edge_inference", "synthetic_load"}
CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/-]{1,119}$")
MAX_SAMPLES = 100_000
MAX_TEXT = 500


class BenchmarkValidationError(ValueError):
    """Raised when a benchmark record cannot be safely normalized."""


def _text(value: Any, field: str, *, required: bool = True) -> str | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        if required:
            raise BenchmarkValidationError(f"Champ obligatoire manquant : {field}.")
        return None
    if not isinstance(value, str):
        raise BenchmarkValidationError(f"Le champ {field} doit être du texte.")
    result = value.strip()
    if len(result) > MAX_TEXT:
        raise BenchmarkValidationError(f"Le champ {field} dépasse {MAX_TEXT} caractères.")
    return result


def _identifier(value: Any, field: str) -> str:
    result = _text(value, field)
    if not IDENTIFIER_RE.fullmatch(result or ""):
        raise BenchmarkValidationError(f"Identifiant invalide : {field}.")
    return result or ""


def _timestamp(value: Any, field: str) -> datetime:
    raw = _text(value, field)
    try:
        parsed = datetime.fromisoformat((raw or "").replace("Z", "+00:00"))
    except ValueError as exc:
        raise BenchmarkValidationError(f"Date ISO 8601 invalide : {field}.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise BenchmarkValidationError(f"Date {field} sans fuseau horaire.")
    return parsed


def _finite_nonnegative(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise BenchmarkValidationError(f"{field} doit être numérique.")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise BenchmarkValidationError(f"{field} doit être fini et positif ou nul.")
    return number


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    # Nearest-rank percentile, with rank bounded to [1, n].
    rank = max(1, math.ceil((percentile / 100.0) * len(ordered)))
    return ordered[rank - 1]


def prepare_benchmark_record(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate actual supplied observations and return a non-publishable draft."""
    if not isinstance(payload, dict):
        raise BenchmarkValidationError("La soumission doit être un objet.")

    allowed = {
        "benchmark_id", "workload_id", "workload_type", "resource_id",
        "resource_type", "provider_or_operator", "region", "started_at",
        "ended_at", "latency_samples_ms", "attempts", "successes",
        "cost_amount", "cost_currency", "cost_basis", "software_version",
        "hardware_profile", "configuration_ref", "artifact_ref", "operator",
        "notes",
    }
    unknown = set(payload) - allowed
    if unknown:
        raise BenchmarkValidationError("Champs non autorisés : " + ", ".join(sorted(unknown)))

    started = _timestamp(payload.get("started_at"), "started_at")
    ended = _timestamp(payload.get("ended_at"), "ended_at")
    if ended <= started:
        raise BenchmarkValidationError("La fin du test doit être postérieure au début.")

    workload_type = _text(payload.get("workload_type"), "workload_type")
    resource_type = _text(payload.get("resource_type"), "resource_type")
    if workload_type not in ALLOWED_WORKLOADS:
        raise BenchmarkValidationError("Type de charge non autorisé.")
    if resource_type not in ALLOWED_RESOURCE_TYPES:
        raise BenchmarkValidationError("Type de ressource non autorisé.")

    raw_samples = payload.get("latency_samples_ms")
    if not isinstance(raw_samples, list) or not raw_samples or len(raw_samples) > MAX_SAMPLES:
        raise BenchmarkValidationError("Fournir entre 1 et 100000 mesures de latence.")
    samples = [_finite_nonnegative(item, "latency_samples_ms") for item in raw_samples]

    attempts = payload.get("attempts")
    successes = payload.get("successes")
    if isinstance(attempts, bool) or not isinstance(attempts, int) or attempts < 1:
        raise BenchmarkValidationError("attempts doit être un entier positif.")
    if isinstance(successes, bool) or not isinstance(successes, int) or not 0 <= successes <= attempts:
        raise BenchmarkValidationError("successes doit être compris entre 0 et attempts.")
    if len(samples) > successes:
        raise BenchmarkValidationError("Les latences ne peuvent dépasser le nombre de succès.")

    cost_amount = _finite_nonnegative(payload.get("cost_amount"), "cost_amount")
    currency = _text(payload.get("cost_currency"), "cost_currency")
    if not CURRENCY_RE.fullmatch(currency or ""):
        raise BenchmarkValidationError("La devise doit être un code ISO 4217 à trois lettres.")

    record = {
        "benchmark_id": _identifier(payload.get("benchmark_id"), "benchmark_id"),
        "workload_id": _identifier(payload.get("workload_id"), "workload_id"),
        "workload_type": workload_type,
        "resource_id": _identifier(payload.get("resource_id"), "resource_id"),
        "resource_type": resource_type,
        "provider_or_operator": _text(payload.get("provider_or_operator"), "provider_or_operator"),
        "region": _text(payload.get("region"), "region"),
        "started_at": started.isoformat(),
        "ended_at": ended.isoformat(),
        "duration_seconds": (ended - started).total_seconds(),
        "latency_samples_ms": samples,
        "latency_summary_ms": {
            "min": min(samples),
            "median_nearest_rank": _percentile(samples, 50),
            "p95_nearest_rank": _percentile(samples, 95),
            "max": max(samples),
            "sample_count": len(samples),
        },
        "availability": {
            "attempts": attempts,
            "successes": successes,
            "failures": attempts - successes,
            "success_rate": successes / attempts,
        },
        "cost": {
            "amount": cost_amount,
            "currency": currency,
            "basis": _text(payload.get("cost_basis"), "cost_basis"),
        },
        "software_version": _text(payload.get("software_version"), "software_version"),
        "hardware_profile": _text(payload.get("hardware_profile"), "hardware_profile"),
        "configuration_ref": _text(payload.get("configuration_ref"), "configuration_ref"),
        "artifact_ref": _text(payload.get("artifact_ref"), "artifact_ref"),
        "operator": _text(payload.get("operator"), "operator"),
        "notes": _text(payload.get("notes"), "notes", required=False),
        # Client-submitted measurements are claims until independently reviewed.
        "evidence_status": "pending",
        "publication_state": "draft",
        "approved_by": None,
        "published_at": None,
    }
    # Fingerprint the normalized submitted record for later integrity checks.
    # This is a content hash, not a digital signature or proof of execution.
    canonical = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    record["record_fingerprint_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return record

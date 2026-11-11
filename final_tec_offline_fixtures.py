"""G1 offline evaluator for fixed synthetic fixtures.

This module evaluates bundled constant data only. It does not execute user code,
spawn processes, open sockets, access files, call providers, or measure hardware.
All outputs are synthetic demonstrations and remain pending/draft.
"""
from __future__ import annotations

from datetime import datetime
import math
from typing import Any, Mapping

from final_tec_runner_policy import RunPolicyError, validate_run_manifest


_FIXTURES: dict[str, dict[str, Any]] = {
    "latency_smoke": {
        "description": "Small deterministic latency sample (synthetic milliseconds).",
        "latency_ms": (1.0, 2.0, 2.0, 3.0, 5.0),
        "requests": 5,
        "successes": 5,
    },
    "mixed_smoke": {
        "description": "Small deterministic mixed-result sample (synthetic milliseconds).",
        "latency_ms": (2.0, 3.0, 5.0, 8.0, 13.0),
        "requests": 5,
        "successes": 4,
    },
}


def available_fixtures() -> tuple[str, ...]:
    """Return the fixed fixture identifiers; no dynamic fixture loading."""
    return tuple(sorted(_FIXTURES))


def _nearest_rank(values: tuple[float, ...], percentile: float) -> float:
    ordered = sorted(values)
    rank = max(1, math.ceil(percentile * len(ordered)))
    return ordered[rank - 1]


def evaluate_offline_fixture(
    manifest: Mapping[str, Any],
    fixture_id: str,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Evaluate bundled synthetic data after the G0 policy gate passes.

    G1 deliberately does not execute a workload. The manifest must be explicitly
    local, network-disabled, zero-cost and tightly bounded. Unknown fixture IDs
    fail closed.
    """
    if not isinstance(fixture_id, str) or fixture_id not in _FIXTURES:
        raise RunPolicyError("Fixture G1 inconnu ou non autorisé.")

    policy = validate_run_manifest(manifest, now=now)
    if policy["resource_id"] != "resource-sandbox":
        raise RunPolicyError("G1 accepte uniquement la ressource locale sandbox.")
    if policy["cost_basis"] != "local_fixture" or policy["estimated_cost"] != 0.0:
        raise RunPolicyError("G1 exige un fixture local à coût nul.")
    if policy["network_enabled"] is not False:
        raise RunPolicyError("G1 interdit tout accès réseau.")
    limits = policy["limits"]
    if (
        limits["max_duration_seconds"] > 30
        or limits["max_requests"] > 100
        or limits["max_repetitions"] > 10
        or limits["max_cpu_cores"] > 2
        or limits["max_memory_mb"] > 512
        or limits["max_artifact_bytes"] > 1_048_576
    ):
        raise RunPolicyError("Une limite du profil G1 local est dépassée.")

    fixture = _FIXTURES[fixture_id]
    if fixture["requests"] > limits["max_requests"]:
        raise RunPolicyError("Le fixture dépasse le plafond de requêtes autorisé.")

    latencies = fixture["latency_ms"]
    return {
        "run_id": policy["run_id"],
        "fixture_id": fixture_id,
        "description": fixture["description"],
        "execution_kind": "synthetic_fixture_evaluation",
        "workload_executed": False,
        "network_used": False,
        "provider_contacted": False,
        "cost": 0.0,
        "currency": policy["currency"],
        "sample_count": len(latencies),
        "requests": fixture["requests"],
        "successes": fixture["successes"],
        "failures": fixture["requests"] - fixture["successes"],
        "success_rate_percent": round(
            fixture["successes"] / fixture["requests"] * 100, 2
        ),
        "latency_ms": {
            "min": min(latencies),
            "p50": _nearest_rank(latencies, 0.50),
            "p95": _nearest_rank(latencies, 0.95),
            "max": max(latencies),
        },
        "evidence_status": "pending",
        "publication_state": "draft",
        "notice": "Données synthétiques fixes ; aucune mesure matérielle ou performance réelle.",
    }

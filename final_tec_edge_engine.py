"""Explainable, offline FINAL TEC Edge resource selection simulation.

This module only evaluates an explicitly supplied allowlist and published,
verified benchmark records. It never dispatches workloads or contacts providers.
"""
from __future__ import annotations
from datetime import datetime, timezone
import math
from typing import Any


class EdgeSelectionError(ValueError):
    """Raised when a task profile or candidate input is invalid."""


DEFAULT_WEIGHTS = {"latency": 0.40, "availability": 0.35, "cost": 0.25}


def _aware_datetime(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise EdgeSelectionError(f"{field} must be an ISO-8601 timestamp.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EdgeSelectionError(f"{field} must be an ISO-8601 timestamp.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise EdgeSelectionError(f"{field} must include a timezone.")
    return parsed.astimezone(timezone.utc)


def _number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EdgeSelectionError(f"{field} must be numeric.")
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise EdgeSelectionError(f"{field} must be finite and non-negative.")
    return result


def _validate_profile(profile: dict[str, Any]) -> dict[str, Any]:
    required = {"workload_type", "region", "max_latency_ms", "min_success_rate",
                "max_cost_amount", "currency", "cost_basis"}
    if not isinstance(profile, dict) or set(profile) - (required | {"required_features"}):
        raise EdgeSelectionError("Task profile has unknown fields or is not an object.")
    missing = required - set(profile)
    if missing:
        raise EdgeSelectionError("Missing task profile fields: " + ", ".join(sorted(missing)))
    if not all(isinstance(profile[k], str) and profile[k].strip()
               for k in ("workload_type", "region", "currency", "cost_basis")):
        raise EdgeSelectionError("Workload, region, currency and cost basis must be non-empty text.")
    latency = _number(profile["max_latency_ms"], "max_latency_ms")
    rate = _number(profile["min_success_rate"], "min_success_rate")
    cost = _number(profile["max_cost_amount"], "max_cost_amount")
    if latency <= 0 or rate > 1:
        raise EdgeSelectionError("Latency must be positive and success rate between 0 and 1.")
    features = profile.get("required_features", [])
    if not isinstance(features, list) or any(not isinstance(x, str) or not x.strip() for x in features):
        raise EdgeSelectionError("required_features must be a list of non-empty strings.")
    return {**profile, "max_latency_ms": latency, "min_success_rate": rate,
            "max_cost_amount": cost, "required_features": sorted(set(features))}


def _validate_weights(weights: dict[str, Any] | None) -> dict[str, float]:
    chosen = DEFAULT_WEIGHTS if weights is None else weights
    if not isinstance(chosen, dict) or set(chosen) != set(DEFAULT_WEIGHTS):
        raise EdgeSelectionError("Weights must define latency, availability and cost only.")
    parsed = {key: _number(value, f"weight.{key}") for key, value in chosen.items()}
    if sum(parsed.values()) <= 0:
        raise EdgeSelectionError("Weights must have a positive sum.")
    total = sum(parsed.values())
    return {key: value / total for key, value in parsed.items()}


def select_edge_resources(task_profile: dict[str, Any], candidates: list[dict[str, Any]],
                          *, now: str, max_age_seconds: int = 86400,
                          weights: dict[str, Any] | None = None) -> dict[str, Any]:
    """Rank authorized candidates; return an explainable simulation, never execute."""
    profile = _validate_profile(task_profile)
    current = _aware_datetime(now, "now")
    if isinstance(max_age_seconds, bool) or not isinstance(max_age_seconds, int) or max_age_seconds < 1:
        raise EdgeSelectionError("max_age_seconds must be a positive integer.")
    normalized_weights = _validate_weights(weights)
    if not isinstance(candidates, list):
        raise EdgeSelectionError("candidates must be a list.")

    evaluated = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            raise EdgeSelectionError("Each candidate must be an object.")
        resource_id = candidate.get("resource_id")
        if not isinstance(resource_id, str) or not resource_id.strip():
            raise EdgeSelectionError("Each candidate needs a resource_id.")
        reasons = []
        benchmark = candidate.get("benchmark")
        features = candidate.get("features", [])
        if not isinstance(features, list) or any(not isinstance(x, str) for x in features):
            raise EdgeSelectionError(f"Invalid features for {resource_id}.")
        if candidate.get("authorized") is not True:
            reasons.append("resource_not_explicitly_authorized")
        if not isinstance(benchmark, dict):
            reasons.append("benchmark_missing")
            benchmark = {}
        if benchmark.get("evidence_status") != "verified" or benchmark.get("publication_state") != "published":
            reasons.append("benchmark_not_verified_and_published")
        if benchmark.get("workload_type") != profile["workload_type"]:
            reasons.append("workload_mismatch")
        if benchmark.get("region") != profile["region"]:
            reasons.append("region_mismatch")
        summary, availability, cost = (benchmark.get("latency_summary_ms"),
                                       benchmark.get("availability"), benchmark.get("cost"))
        if not all(isinstance(x, dict) for x in (summary, availability, cost)):
            reasons.append("benchmark_metrics_missing")
            summary = summary if isinstance(summary, dict) else {}
            availability = availability if isinstance(availability, dict) else {}
            cost = cost if isinstance(cost, dict) else {}
        try:
            p95 = _number(summary.get("p95_nearest_rank"), "p95_nearest_rank")
            success_rate = _number(availability.get("success_rate"), "success_rate")
            amount = _number(cost.get("amount"), "cost.amount")
            if success_rate > 1:
                raise EdgeSelectionError("success_rate must be between 0 and 1.")
        except EdgeSelectionError:
            p95 = success_rate = amount = None
            reasons.append("benchmark_metrics_invalid")
        if cost.get("currency") != profile["currency"] or cost.get("basis") != profile["cost_basis"]:
            reasons.append("cost_unit_or_currency_mismatch")
        if not set(profile["required_features"]).issubset(set(features)):
            reasons.append("required_features_missing")
        ended_at = benchmark.get("ended_at")
        try:
            ended = _aware_datetime(ended_at, "benchmark.ended_at")
            age = (current - ended).total_seconds()
            if age < 0:
                reasons.append("benchmark_timestamp_in_future")
            elif age > max_age_seconds:
                reasons.append("benchmark_stale")
        except EdgeSelectionError:
            age = None
            reasons.append("benchmark_timestamp_invalid")
        if p95 is not None and p95 > profile["max_latency_ms"]:
            reasons.append("latency_ceiling_exceeded")
        if success_rate is not None and success_rate < profile["min_success_rate"]:
            reasons.append("availability_below_minimum")
        if amount is not None and amount > profile["max_cost_amount"]:
            reasons.append("budget_ceiling_exceeded")

        item = {"resource_id": resource_id, "eligible": not reasons, "exclusion_reasons": reasons,
                "benchmark_id": benchmark.get("benchmark_id"),
                "benchmark_ended_at": ended_at if isinstance(ended_at, str) else None}
        if not reasons:
            components = {
                "latency": max(0.0, 1.0 - p95 / profile["max_latency_ms"]),
                "availability": success_rate,
                "cost": (1.0 if amount == 0 else max(0.0, 1.0 - amount / profile["max_cost_amount"]))
                        if profile["max_cost_amount"] > 0 else 1.0,
            }
            item.update({
                "score": round(sum(components[k] * normalized_weights[k] for k in components), 6),
                "score_components": {k: round(v, 6) for k, v in components.items()},
                "weights": normalized_weights, "measured_p95_ms": p95,
                "measured_success_rate": success_rate,
                "measured_cost": {"amount": amount, "currency": cost["currency"], "basis": cost["basis"]},
                "age_seconds": round(age, 3),
            })
        evaluated.append(item)

    evaluated.sort(key=lambda x: (not x["eligible"], -x.get("score", -1), x["resource_id"]))
    eligible = [x for x in evaluated if x["eligible"]]
    return {
        "mode": "offline_simulation",
        "decision": "recommendation" if eligible else "no_eligible_resource",
        "selected_resource_id": eligible[0]["resource_id"] if eligible else None,
        "ranking": eligible, "excluded": [x for x in evaluated if not x["eligible"]],
        "weights": normalized_weights,
        "side_effects": {"provider_calls": False, "workload_dispatch": False,
                         "resource_provisioning": False, "spending": False, "database_writes": False},
        "notice": "Simulation uniquement : aucune ressource n'est réservée ni exécutée.",
    }

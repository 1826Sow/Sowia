from datetime import datetime, timezone

import pytest

from final_tec_offline_fixtures import (
    available_fixtures,
    evaluate_offline_fixture,
)
from final_tec_runner_policy import RunPolicyError


NOW = datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc)


def valid_g1_manifest():
    return {
        "run_id": "g1-fixture-001",
        "approval_ref": "approval-g1-001",
        "operator_id": "operator-local",
        "resource_id": "resource-sandbox",
        "authorization_status": "approved",
        "expires_at": "2026-11-12T12:00:00Z",
        "network_enabled": False,
        "budget_limit": 0.0 + 1.0,
        "estimated_cost": 0.0,
        "currency": "EUR",
        "cost_basis": "local_fixture",
        "max_duration_seconds": 30,
        "max_requests": 100,
        "max_repetitions": 10,
        "max_cpu_cores": 2,
        "max_memory_mb": 512,
        "max_artifact_bytes": 1_048_576,
        "emergency_stop": False,
    }


def test_only_fixed_bundled_fixtures_are_available():
    assert available_fixtures() == ("latency_smoke", "mixed_smoke")


def test_latency_fixture_is_synthetic_and_never_published():
    result = evaluate_offline_fixture(valid_g1_manifest(), "latency_smoke", now=NOW)
    assert result["execution_kind"] == "synthetic_fixture_evaluation"
    assert result["workload_executed"] is False
    assert result["network_used"] is False
    assert result["provider_contacted"] is False
    assert result["cost"] == 0.0
    assert result["sample_count"] == 5
    assert result["latency_ms"] == {"min": 1.0, "p50": 2.0, "p95": 5.0, "max": 5.0}
    assert result["success_rate_percent"] == 100.0
    assert result["evidence_status"] == "pending"
    assert result["publication_state"] == "draft"


def test_mixed_fixture_keeps_failures_visible():
    result = evaluate_offline_fixture(valid_g1_manifest(), "mixed_smoke", now=NOW)
    assert result["successes"] == 4
    assert result["failures"] == 1
    assert result["success_rate_percent"] == 80.0


def test_unknown_fixture_fails_closed():
    with pytest.raises(RunPolicyError, match="inconnu"):
        evaluate_offline_fixture(valid_g1_manifest(), "../external", now=NOW)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("resource_id", "remote-provider"),
        ("cost_basis", "provider_quote"),
        ("estimated_cost", 0.01),
        ("network_enabled", True),
        ("max_duration_seconds", 31),
        ("max_requests", 101),
        ("max_repetitions", 11),
        ("max_cpu_cores", 2.1),
        ("max_memory_mb", 513),
        ("max_artifact_bytes", 1_048_577),
    ],
)
def test_g1_profile_rejects_remote_costly_or_unbounded_manifest(field, value):
    manifest = valid_g1_manifest()
    manifest[field] = value
    with pytest.raises(RunPolicyError):
        evaluate_offline_fixture(manifest, "latency_smoke", now=NOW)


def test_fixture_request_count_must_fit_manifest_limit():
    manifest = valid_g1_manifest()
    manifest["max_requests"] = 4
    with pytest.raises(RunPolicyError, match="requêtes"):
        evaluate_offline_fixture(manifest, "latency_smoke", now=NOW)

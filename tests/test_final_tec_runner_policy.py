from datetime import datetime, timezone

import pytest

from final_tec_runner_policy import (
    RunPolicyError,
    transition_run_state,
    validate_run_manifest,
)


NOW = datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc)


def valid_manifest():
    return {
        "run_id": "run-g0-001",
        "approval_ref": "approval-001",
        "operator_id": "operator-local",
        "resource_id": "resource-sandbox",
        "authorization_status": "approved",
        "expires_at": "2026-11-12T12:00:00Z",
        "network_enabled": False,
        "budget_limit": 1.0,
        "estimated_cost": 0.0,
        "currency": "EUR",
        "cost_basis": "local_fixture",
        "max_duration_seconds": 300,
        "max_requests": 100,
        "max_repetitions": 5,
        "max_cpu_cores": 2,
        "max_memory_mb": 512,
        "max_artifact_bytes": 1048576,
        "emergency_stop": False,
    }


def test_valid_manifest_is_only_locally_validated_and_not_published():
    result = validate_run_manifest(valid_manifest(), now=NOW)
    assert result["policy_result"] == "locally_validated_not_executed"
    assert result["evidence_status"] == "pending"
    assert result["publication_state"] == "draft"
    assert result["network_enabled"] is False
    assert result["estimated_cost"] == 0.0


@pytest.mark.parametrize("field", [
    "run_id", "approval_ref", "operator_id", "resource_id",
    "authorization_status", "expires_at", "network_enabled",
    "budget_limit", "estimated_cost", "currency", "cost_basis",
    "max_duration_seconds", "max_requests", "max_repetitions",
    "max_cpu_cores", "max_memory_mb", "max_artifact_bytes",
    "emergency_stop",
])
def test_missing_required_field_fails_closed(field):
    manifest = valid_manifest()
    del manifest[field]
    with pytest.raises(RunPolicyError):
        validate_run_manifest(manifest, now=NOW)


@pytest.mark.parametrize(("field", "value"), [
    ("authorization_status", "pending"),
    ("network_enabled", True),
    ("emergency_stop", True),
    ("currency", "EU"),
    ("expires_at", "2026-11-11T11:59:59Z"),
    ("budget_limit", True),
    ("estimated_cost", float("inf")),
    ("max_requests", 0),
    ("max_duration_seconds", 86401),
    ("max_cpu_cores", 65),
    ("max_artifact_bytes", 2_000_000_000),
])
def test_unsafe_or_invalid_values_are_rejected(field, value):
    manifest = valid_manifest()
    manifest[field] = value
    with pytest.raises(RunPolicyError):
        validate_run_manifest(manifest, now=NOW)


def test_estimated_cost_cannot_exceed_budget():
    manifest = valid_manifest()
    manifest["estimated_cost"] = 1.01
    with pytest.raises(RunPolicyError, match="dépasse le budget"):
        validate_run_manifest(manifest, now=NOW)


def test_unknown_fields_are_rejected():
    manifest = valid_manifest()
    manifest["secret_key"] = "must-not-be-accepted"
    with pytest.raises(RunPolicyError, match="non autorisés"):
        validate_run_manifest(manifest, now=NOW)


def test_timezone_is_required_for_expiration():
    manifest = valid_manifest()
    manifest["expires_at"] = "2026-11-12T12:00:00"
    with pytest.raises(RunPolicyError, match="fuseau horaire"):
        validate_run_manifest(manifest, now=NOW)


def test_boolean_is_not_accepted_as_numeric_limit():
    manifest = valid_manifest()
    manifest["max_requests"] = True
    with pytest.raises(RunPolicyError):
        validate_run_manifest(manifest, now=NOW)


def test_state_machine_allows_only_explicit_progression():
    assert transition_run_state("draft", "submitted") == "submitted"
    assert transition_run_state("submitted", "authorized") == "authorized"
    assert transition_run_state("authorized", "prepared") == "prepared"
    assert transition_run_state("prepared", "running") == "running"
    assert transition_run_state("running", "completed") == "completed"
    assert transition_run_state("completed", "pending_review") == "pending_review"


def test_state_machine_rejects_skipping_review():
    with pytest.raises(RunPolicyError):
        transition_run_state("running", "pending_review")
    with pytest.raises(RunPolicyError):
        transition_run_state("completed", "published")


def test_emergency_stop_aborts_active_run():
    assert transition_run_state("running", "aborted", emergency_stop=True) == "aborted"


def test_emergency_stop_never_allows_progress():
    with pytest.raises(RunPolicyError):
        transition_run_state("running", "completed", emergency_stop=True)


def test_terminal_states_cannot_restart():
    with pytest.raises(RunPolicyError):
        transition_run_state("aborted", "running")

"""Integration tests for the SQLite nonce registry and G0-G2-B validator."""
import base64
from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest

from final_tec_authorization_contract import (
    AuthorizationContractError,
    validate_authorization_contract,
)
from final_tec_nonce_registry import SQLiteNonceRegistry


def make_contract(now):
    return {
        "schema_version": "1.0",
        "authorization_id": "auth-integration-001",
        "run_id": "run-integration-001",
        "nonce": "integration-nonce-" + ("x" * 40),
        "issued_at": (now - timedelta(minutes=1)).isoformat(),
        "expires_at": (now + timedelta(minutes=15)).isoformat(),
        "revoked_at": None,
        "status": "approved",
        "scenario_id": "benign-local-smoke-v1",
        "actors": {
            "requester_id": "requester-1",
            "approver_id": "approver-1",
            "operator_id": "operator-1",
            "reviewer_id": "reviewer-1",
        },
        "approval": {
            "approver_role": "security-approver",
            "approval_policy_id": "policy-v1",
            "algorithm": "Ed25519",
            "key_id": "integration-test-key",
            "signature": base64.b64encode(b"z" * 64).decode("ascii"),
        },
        "environment": {
            "host_id": "host-disposable-integration",
            "host_os": "linux integration test",
            "kernel_version": "test kernel",
            "architecture": "x86_64",
            "runtime_name": "test-runtime",
            "runtime_version": "1.0",
            "runtime_config_digest": "a" * 64,
            "image_digest": "b" * 64,
            "g2a_profile_digest": "c" * 64,
            "workload_digest": "d" * 64,
        },
        "constraints": {
            "network_policy": "deny_all",
            "secrets_policy": "none",
            "cpu_limit": 1,
            "memory_limit_bytes": 268435456,
            "pids_limit": 16,
            "io_limit_bytes": 1048576,
            "scratch_limit_bytes": 1048576,
            "output_limit_bytes": 65536,
            "timeout_seconds": 10,
            "budget_limit": 0,
            "currency": "EUR",
            "stop_controller_id": "stop-controller-test",
            "stop_policy_version": "stop-v1",
        },
    }


def run_validation(contract, store, now, *, identity_ok=True):
    return validate_authorization_contract(
        contract,
        expected_environment=deepcopy(contract["environment"]),
        signature_verifier=lambda payload, approval: True,
        identity_verifier=lambda approver_id, role: identity_ok,
        nonce_consumer=store.consume_callback,
        now=now,
    )


def test_validator_consumes_sqlite_nonce_and_rejects_replay(tmp_path):
    now = datetime.now(timezone.utc)
    contract = make_contract(now)
    store = SQLiteNonceRegistry(tmp_path / "integration.sqlite3")
    expiry = datetime.fromisoformat(contract["expires_at"])
    assert store.register(contract["nonce"], contract["authorization_id"], expiry)

    result = run_validation(contract, store, now)
    assert result["contract_result"] == "contract_validated_not_execution_authorized"
    assert result["nonce_consumed_by_injected_store"] is True
    assert result["workload_executed"] is False

    with pytest.raises(AuthorizationContractError, match="Nonce"):
        run_validation(contract, store, now)


def test_failed_identity_check_does_not_burn_sqlite_nonce(tmp_path):
    now = datetime.now(timezone.utc)
    contract = make_contract(now)
    store = SQLiteNonceRegistry(tmp_path / "identity.sqlite3")
    expiry = datetime.fromisoformat(contract["expires_at"])
    assert store.register(contract["nonce"], contract["authorization_id"], expiry)

    with pytest.raises(AuthorizationContractError, match="Identité"):
        run_validation(contract, store, now, identity_ok=False)

    result = run_validation(contract, store, now)
    assert result["nonce_consumed_by_injected_store"] is True

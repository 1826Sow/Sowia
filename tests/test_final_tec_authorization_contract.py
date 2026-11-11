from copy import deepcopy
from datetime import datetime, timezone

import pytest

from final_tec_authorization_contract import (
    AuthorizationContractError,
    validate_authorization_contract,
)


NOW = datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc)
DIGEST = "a" * 64


def valid_contract():
    return {
        "schema_version": "1.0",
        "authorization_id": "auth-001",
        "run_id": "run-001",
        "nonce": "n" * 48,
        "issued_at": "2026-11-11T11:00:00Z",
        "expires_at": "2026-11-11T13:00:00Z",
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
            "key_id": "test-key-1",
            "signature": "S" * 88,
        },
        "environment": {
            "host_id": "host-disposable-1",
            "host_os": "linux-test",
            "kernel_version": "test-kernel-1",
            "architecture": "x86_64",
            "runtime_name": "runtime-test",
            "runtime_version": "1.0.0",
            "runtime_config_digest": DIGEST,
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


def environment(contract=None):
    contract = contract or valid_contract()
    return deepcopy(contract["environment"])


def callbacks(*, signature=True, identity=True, nonce=True, calls=None):
    calls = calls if calls is not None else []
    def verify_signature(payload, approval):
        calls.append("signature")
        return signature
    def verify_identity(approver_id, role):
        calls.append("identity")
        return identity
    def consume_nonce(value, authorization_id):
        calls.append("nonce")
        return nonce
    return verify_signature, verify_identity, consume_nonce, calls


def validate(contract=None, *, signature=True, identity=True, nonce=True, expected=None, calls=None):
    contract = contract or valid_contract()
    sv, iv, nc, calls = callbacks(
        signature=signature, identity=identity, nonce=nonce, calls=calls
    )
    return validate_authorization_contract(
        contract,
        expected_environment=expected or environment(contract),
        signature_verifier=sv,
        identity_verifier=iv,
        nonce_consumer=nc,
        now=NOW,
    )


def test_valid_contract_is_not_execution_authorization():
    result = validate()
    assert result["contract_result"] == "contract_validated_not_execution_authorized"
    assert result["host_controls_verified"] is False
    assert result["workload_executed"] is False
    assert result["evidence_status"] == "pending"
    assert result["publication_state"] == "draft"


@pytest.mark.parametrize("field", [
    "schema_version", "authorization_id", "run_id", "nonce", "issued_at",
    "expires_at", "revoked_at", "status", "scenario_id", "actors",
    "approval", "environment", "constraints",
])
def test_missing_top_level_field_fails_closed(field):
    contract = valid_contract()
    del contract[field]
    with pytest.raises(AuthorizationContractError):
        validate(contract)


def test_unknown_top_level_field_fails_closed():
    contract = valid_contract()
    contract["unexpected"] = "not-allowed"
    with pytest.raises(AuthorizationContractError):
        validate(contract)


@pytest.mark.parametrize(("path", "value"), [
    (("status",), "pending"),
    (("schema_version",), "2.0"),
    (("nonce",), "short"),
    (("issued_at",), "2026-11-11T13:00:00Z"),
    (("expires_at",), "2026-11-11T11:59:00Z"),
    (("revoked_at",), "2026-11-11T11:30:00Z"),
    (("approval", "algorithm"), "HS256"),
    (("constraints", "network_policy"), "allow_all"),
    (("constraints", "secrets_policy"), "environment"),
    (("constraints", "budget_limit"), 0.01),
    (("constraints", "cpu_limit"), 100),
    (("constraints", "pids_limit"), 0),
])
def test_invalid_or_unsafe_values_fail_closed(path, value):
    contract = valid_contract()
    target = contract
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(AuthorizationContractError):
        validate(contract)


@pytest.mark.parametrize("actor_pair", [
    ("requester_id", "approver_id"),
    ("operator_id", "reviewer_id"),
    ("approver_id", "reviewer_id"),
])
def test_incompatible_actor_roles_must_be_distinct(actor_pair):
    contract = valid_contract()
    contract["actors"][actor_pair[1]] = contract["actors"][actor_pair[0]]
    with pytest.raises(AuthorizationContractError):
        validate(contract)


@pytest.mark.parametrize("field", [
    "runtime_config_digest", "image_digest", "g2a_profile_digest", "workload_digest",
])
def test_environment_digests_must_be_sha256(field):
    contract = valid_contract()
    contract["environment"][field] = "not-a-digest"
    with pytest.raises(AuthorizationContractError):
        validate(contract)


def test_environment_substitution_fails_closed():
    contract = valid_contract()
    expected = environment(contract)
    expected["image_digest"] = "e" * 64
    with pytest.raises(AuthorizationContractError, match="environnement observé"):
        validate(contract, expected=expected)


def test_invalid_identity_fails_before_signature_or_nonce_consumption():
    calls = []
    with pytest.raises(AuthorizationContractError, match="Identité"):
        validate(identity=False, calls=calls)
    assert calls == ["identity"]


def test_invalid_signature_fails_before_nonce_consumption():
    calls = []
    with pytest.raises(AuthorizationContractError, match="Signature invalide"):
        validate(signature=False, calls=calls)
    assert calls == ["identity", "signature"]


def test_nonce_is_consumed_only_after_identity_and_signature_checks():
    calls = []
    validate(calls=calls)
    assert calls == ["identity", "signature", "nonce"]


def test_replayed_or_unavailable_nonce_fails_closed():
    with pytest.raises(AuthorizationContractError, match="Nonce"):
        validate(nonce=False)


def test_unknown_approval_fields_are_rejected():
    contract = valid_contract()
    contract["approval"]["private_key"] = "must-not-be-here"
    with pytest.raises(AuthorizationContractError):
        validate(contract)


def test_naive_clock_is_rejected():
    contract = valid_contract()
    sv, iv, nc, _ = callbacks()
    with pytest.raises(AuthorizationContractError, match="fuseau horaire"):
        validate_authorization_contract(
            contract,
            expected_environment=environment(contract),
            signature_verifier=sv,
            identity_verifier=iv,
            nonce_consumer=nc,
            now=datetime(2026, 11, 11, 12, 0),
        )

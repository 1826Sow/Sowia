from copy import deepcopy
import base64
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from final_tec_authorization_contract import (
    AuthorizationContractError,
    validate_authorization_contract,
)
from final_tec_ed25519_verifier import (
    ApprovalVerificationError,
    Ed25519ApprovalVerifier,
    TrustedApprovalKey,
)


def _raw_public(private_key):
    return private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)


def _fixture():
    now = datetime.now(timezone.utc)
    private = Ed25519PrivateKey.generate()
    contract = {
        "schema_version": "1.0",
        "authorization_id": "auth-ed25519-001",
        "run_id": "run-ed25519-001",
        "nonce": "n" * 48,
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
            "key_id": "key-current",
            "signature": "",
        },
        "environment": {
            "host_id": "host-test",
            "host_os": "Linux test",
            "kernel_version": "test-kernel",
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
    payload = deepcopy(contract)
    approval_without_signature = dict(payload.pop("approval"))
    approval_without_signature.pop("signature")
    payload["approval"] = approval_without_signature
    signature = private.sign(Ed25519ApprovalVerifier.canonical_payload(payload))
    contract["approval"]["signature"] = base64.b64encode(signature).decode("ascii")
    record = TrustedApprovalKey(
        key_id="key-current",
        approver_id="approver-1",
        approver_role="security-approver",
        public_key_raw=_raw_public(private),
        valid_from=now - timedelta(days=1),
        valid_until=now + timedelta(days=30),
    )
    return now, contract, record


def _validate(contract, verifier, now):
    return validate_authorization_contract(
        contract,
        expected_environment=deepcopy(contract["environment"]),
        signature_verifier=verifier,
        identity_verifier=verifier.verify_identity,
        nonce_consumer=lambda nonce, authorization_id: True,
        now=now,
    )


def test_real_ed25519_signature_validates_contract_without_authorizing_execution():
    now, contract, record = _fixture()
    result = _validate(contract, Ed25519ApprovalVerifier({record.key_id: record}), now)
    assert result["contract_result"] == "contract_validated_not_execution_authorized"
    assert result["signature_verified_by_injected_verifier"] is True
    assert result["workload_executed"] is False


def test_payload_tampering_invalidates_signature():
    now, contract, record = _fixture()
    contract["constraints"]["timeout_seconds"] = 9
    with pytest.raises(AuthorizationContractError, match="Signature invalide"):
        _validate(contract, Ed25519ApprovalVerifier({record.key_id: record}), now)


def test_unknown_key_id_is_rejected():
    now, contract, record = _fixture()
    contract["approval"]["key_id"] = "unknown-key"
    with pytest.raises(AuthorizationContractError, match="Signature invalide"):
        _validate(contract, Ed25519ApprovalVerifier({record.key_id: record}), now)


def test_wrong_public_key_is_rejected():
    now, contract, record = _fixture()
    other = Ed25519PrivateKey.generate()
    wrong = TrustedApprovalKey(
        key_id=record.key_id, approver_id=record.approver_id,
        approver_role=record.approver_role, public_key_raw=_raw_public(other),
        valid_from=record.valid_from, valid_until=record.valid_until,
    )
    with pytest.raises(AuthorizationContractError, match="Signature invalide"):
        _validate(contract, Ed25519ApprovalVerifier({wrong.key_id: wrong}), now)


def test_revoked_key_is_rejected():
    now, contract, record = _fixture()
    revoked = TrustedApprovalKey(
        key_id=record.key_id, approver_id=record.approver_id,
        approver_role=record.approver_role, public_key_raw=record.public_key_raw,
        valid_from=record.valid_from, valid_until=record.valid_until,
        revoked_at=now - timedelta(seconds=1),
    )
    with pytest.raises(AuthorizationContractError, match="Signature invalide"):
        _validate(contract, Ed25519ApprovalVerifier({revoked.key_id: revoked}), now)


def test_expired_key_is_rejected():
    now, contract, record = _fixture()
    expired = TrustedApprovalKey(
        key_id=record.key_id, approver_id=record.approver_id,
        approver_role=record.approver_role, public_key_raw=record.public_key_raw,
        valid_from=now - timedelta(days=3), valid_until=now - timedelta(seconds=1),
    )
    with pytest.raises(AuthorizationContractError, match="Signature invalide"):
        _validate(contract, Ed25519ApprovalVerifier({expired.key_id: expired}), now)


def test_key_rotation_supports_new_key_and_old_verification_only_key():
    now, contract, old_record = _fixture()
    old_disabled = TrustedApprovalKey(
        key_id=old_record.key_id, approver_id=old_record.approver_id,
        approver_role=old_record.approver_role, public_key_raw=old_record.public_key_raw,
        valid_from=old_record.valid_from, valid_until=old_record.valid_until,
        signing_disabled_at=now - timedelta(minutes=30),
    )
    # A signature issued before signing was disabled remains verifiable.
    verifier = Ed25519ApprovalVerifier({
        old_disabled.key_id: old_disabled,
        "key-next": TrustedApprovalKey(
            key_id="key-next", approver_id="approver-1",
            approver_role="security-approver",
            public_key_raw=_raw_public(Ed25519PrivateKey.generate()),
            valid_from=now - timedelta(minutes=1),
            valid_until=now + timedelta(days=30),
        ),
    })
    assert _validate(contract, verifier, now)["workload_executed"] is False


def test_algorithm_substitution_is_rejected():
    now, contract, record = _fixture()
    contract["approval"]["algorithm"] = "HS256"
    with pytest.raises(AuthorizationContractError, match="Algorithme"):
        _validate(contract, Ed25519ApprovalVerifier({record.key_id: record}), now)


def test_approver_or_role_binding_mismatch_is_rejected():
    now, contract, record = _fixture()
    contract["actors"]["approver_id"] = "someone-else"
    with pytest.raises(AuthorizationContractError):
        _validate(contract, Ed25519ApprovalVerifier({record.key_id: record}), now)


def test_non_json_payload_is_rejected_by_canonicalizer():
    with pytest.raises(ApprovalVerificationError):
        Ed25519ApprovalVerifier.canonical_payload({"not_json": object()})

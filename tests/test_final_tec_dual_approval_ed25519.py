import base64
from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from final_tec_dual_approval import (
    DualApprovalError,
    _signed_envelope,
    request_digest,
    validate_dual_approval,
)
from final_tec_dual_approval_ed25519 import DualApprovalEd25519Verifier
from final_tec_ed25519_verifier import TrustedApprovalKey


def _raw_public(private_key):
    return private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)


def fixture():
    now = datetime.now(timezone.utc)
    request = {
        "authorization_id": "dual-ed25519-001",
        "request_version": "v1",
        "requester_id": "requester-01",
        "operator_id": "operator-01",
        "reviewer_id": "reviewer-01",
        "policy_version": "policy-v1",
        "expires_at": (now + timedelta(minutes=15)).isoformat(),
        "environment_digest": "a" * 64,
        "constraints_digest": "b" * 64,
        "action_digest": "c" * 64,
    }
    private_keys = {
        "approver-01": Ed25519PrivateKey.generate(),
        "approver-02": Ed25519PrivateKey.generate(),
    }
    approvals = []
    trusted = {}
    for index, (subject, private) in enumerate(private_keys.items(), start=1):
        key_id = f"dual-key-{index}"
        approval = {
            "subject_id": subject,
            "role": "security-approver",
            "key_id": key_id,
            "algorithm": "Ed25519",
            "approval_policy_id": "dual-policy-v1",
            "policy_version": "policy-v1",
            "nonce": f"{index}" * 48,
            "issued_at": (now - timedelta(seconds=30)).isoformat(),
            "expires_at": (now + timedelta(minutes=10)).isoformat(),
            "signature": "",
        }
        envelope = _signed_envelope(request, request_digest(request), approval)
        approval["signature"] = base64.b64encode(
            private.sign(DualApprovalEd25519Verifier.canonical_payload(envelope))
        ).decode("ascii")
        approvals.append(approval)
        trusted[key_id] = TrustedApprovalKey(
            key_id=key_id,
            approver_id=subject,
            approver_role="security-approver",
            public_key_raw=_raw_public(private),
            valid_from=now - timedelta(days=1),
            valid_until=now + timedelta(days=1),
        )
    return now, request, approvals, trusted


def run_validation(now, request, approvals, verifier):
    identity_map = {
        "approver-01": "security-approver",
        "approver-02": "security-approver",
    }
    consumed = []
    audit = []

    def identity(subject, role, context):
        # Test-only identity stub. This is NOT an external identity provider.
        return identity_map.get(subject) == role

    def consume_pair(auth_id, records):
        consumed.append((auth_id, records))
        return len(records) == 2

    def append_audit(event):
        audit.append(event)
        return True

    result = validate_dual_approval(
        request, approvals,
        signature_verifier=verifier,
        identity_verifier=identity,
        nonce_pair_consumer=consume_pair,
        audit_append=append_audit,
        now=now,
    )
    return result, consumed, audit


def test_two_real_ed25519_signatures_validate_same_request():
    now, request, approvals, trusted = fixture()
    verifier = DualApprovalEd25519Verifier(trusted)
    result, consumed, audit = run_validation(now, request, approvals, verifier)
    assert result["signatures_verified"] is True
    assert result["execution_authorized"] is False
    assert result["workload_executed"] is False
    assert len(consumed) == 1
    assert len(audit) == 1


def test_modified_request_invalidates_both_real_signatures():
    now, request, approvals, trusted = fixture()
    request["constraints_digest"] = "d" * 64
    with pytest.raises(DualApprovalError, match="signature"):
        run_validation(now, request, approvals, DualApprovalEd25519Verifier(trusted))


def test_unknown_trusted_key_is_rejected():
    now, request, approvals, trusted = fixture()
    approvals[0]["key_id"] = "not-in-trust-registry"
    with pytest.raises(DualApprovalError, match="signature"):
        run_validation(now, request, approvals, DualApprovalEd25519Verifier(trusted))


def test_wrong_public_key_is_rejected():
    now, request, approvals, trusted = fixture()
    wrong_private = Ed25519PrivateKey.generate()
    original = trusted["dual-key-1"]
    trusted["dual-key-1"] = TrustedApprovalKey(
        key_id=original.key_id,
        approver_id=original.approver_id,
        approver_role=original.approver_role,
        public_key_raw=_raw_public(wrong_private),
        valid_from=original.valid_from,
        valid_until=original.valid_until,
    )
    with pytest.raises(DualApprovalError, match="signature"):
        run_validation(now, request, approvals, DualApprovalEd25519Verifier(trusted))


def test_revoked_approver_key_is_rejected():
    now, request, approvals, trusted = fixture()
    original = trusted["dual-key-2"]
    trusted["dual-key-2"] = TrustedApprovalKey(
        key_id=original.key_id,
        approver_id=original.approver_id,
        approver_role=original.approver_role,
        public_key_raw=original.public_key_raw,
        valid_from=original.valid_from,
        valid_until=original.valid_until,
        revoked_at=now - timedelta(seconds=1),
    )
    with pytest.raises(DualApprovalError, match="signature"):
        run_validation(now, request, approvals, DualApprovalEd25519Verifier(trusted))


def test_invalid_signature_encoding_is_rejected():
    now, request, approvals, trusted = fixture()
    approvals[0]["signature"] = "not-base64!"
    with pytest.raises(DualApprovalError, match="signature"):
        run_validation(now, request, approvals, DualApprovalEd25519Verifier(trusted))


def test_external_identity_check_rejects_subject_mismatch_before_signature():
    now, request, approvals, trusted = fixture()
    approvals[0]["subject_id"] = "different-person"
    with pytest.raises(DualApprovalError, match="identity"):
        run_validation(now, request, approvals, DualApprovalEd25519Verifier(trusted))

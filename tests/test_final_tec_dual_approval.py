from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest

from final_tec_dual_approval import (
    DualApprovalError,
    _signed_envelope,
    request_digest,
    validate_dual_approval,
)


def fixture():
    now = datetime.now(timezone.utc)
    request = {
        "authorization_id": "dual-auth-001",
        "request_version": "v1",
        "requester_id": "requester-01",
        "operator_id": "operator-01",
        "reviewer_id": "reviewer-01",
        "policy_version": "policy-v1",
        "expires_at": (now + timedelta(minutes=20)).isoformat(),
        "environment_digest": "a" * 64,
        "constraints_digest": "b" * 64,
        "action_digest": "c" * 64,
    }
    approvals = []
    for subject, key, nonce in (
        ("approver-01", "key-01", "n" * 48),
        ("approver-02", "key-02", "m" * 48),
    ):
        item = {
            "subject_id": subject,
            "role": "security-approver",
            "key_id": key,
            "algorithm": "Ed25519",
            "approval_policy_id": "dual-policy-v1",
            "policy_version": "policy-v1",
            "nonce": nonce,
            "issued_at": (now - timedelta(minutes=1)).isoformat(),
            "expires_at": (now + timedelta(minutes=10)).isoformat(),
            "signature": "",
        }
        approvals.append(item)

    def sign(item):
        digest = request_digest(_signed_envelope(request, request_digest(request), item))
        item["signature"] = f"test-signature:{item['subject_id']}:{digest}"

    for item in approvals:
        sign(item)
    return now, request, approvals


def callbacks(approvals=None, *, nonce_ok=True, audit_ok=True, identity_ok=True):
    trusted = {a["subject_id"]: a["key_id"] for a in (approvals or [])}
    commit_attempts = []
    audit_events = []

    def signature_verifier(envelope, approval):
        expected = f"test-signature:{approval['subject_id']}:{request_digest(envelope)}"
        return approval["signature"] == expected

    def identity_verifier(subject, role, context):
        return identity_ok and trusted.get(subject) == context["approval"]["key_id"] and role == "security-approver"

    def atomic_pair_audit_commit(auth_id, records, event):
        commit_attempts.append((auth_id, records, event))
        if not nonce_ok or not audit_ok or len(records) != 2 or records[0][0] == records[1][0]:
            return False
        audit_events.append(event)
        return True

    return signature_verifier, identity_verifier, atomic_pair_audit_commit, commit_attempts, audit_events


def validate(now, request, approvals, cb):
    signature, identity, atomic_commit, *_ = cb
    return validate_dual_approval(
        request, approvals,
        signature_verifier=signature,
        identity_verifier=identity,
        atomic_pair_audit_commit=atomic_commit,
        now=now,
    )


def test_two_distinct_approvers_verify_same_request_without_authorizing_execution():
    now, request, approvals = fixture()
    cb = callbacks(approvals)
    result = validate(now, request, approvals, cb)
    assert result["approval_result"] == "dual_approval_verified_not_execution_authorized"
    assert result["execution_authorized"] is False
    assert result["workload_executed"] is False
    assert len(cb[-1]) == 1


def test_same_subject_cannot_approve_twice():
    now, request, approvals = fixture()
    approvals[1]["subject_id"] = approvals[0]["subject_id"]
    cb = callbacks(approvals)
    with pytest.raises(DualApprovalError, match="distinct"):
        validate(now, request, approvals, cb)
    assert cb[-2] == []


def test_same_key_cannot_be_used_for_both_approvals():
    now, request, approvals = fixture()
    approvals[1]["key_id"] = approvals[0]["key_id"]
    cb = callbacks(approvals)
    with pytest.raises(DualApprovalError, match="distinct"):
        validate(now, request, approvals, cb)


def test_payload_mutation_invalidates_signatures():
    now, request, approvals = fixture()
    request["constraints_digest"] = "d" * 64
    cb = callbacks(approvals)
    with pytest.raises(DualApprovalError, match="signature"):
        validate(now, request, approvals, cb)


def test_identity_or_role_failure_blocks_before_nonce_consumption():
    now, request, approvals = fixture()
    cb = callbacks(approvals, identity_ok=False)
    with pytest.raises(DualApprovalError, match="identity"):
        validate(now, request, approvals, cb)
    assert cb[-2] == []


def test_nonce_pair_must_be_consumed_atomically_and_successfully():
    now, request, approvals = fixture()
    cb = callbacks(approvals, nonce_ok=False)
    with pytest.raises(DualApprovalError, match="Atomic nonce-pair"):
        validate(now, request, approvals, cb)
    assert cb[-1] == []


def test_expired_request_is_rejected():
    now, request, approvals = fixture()
    request["expires_at"] = (now - timedelta(seconds=1)).isoformat()
    cb = callbacks(approvals)
    with pytest.raises(DualApprovalError, match="expired"):
        validate(now, request, approvals, cb)


def test_approver_cannot_be_requester_operator_or_reviewer():
    now, request, approvals = fixture()
    approvals[0]["subject_id"] = request["operator_id"]
    cb = callbacks(approvals)
    with pytest.raises(DualApprovalError, match="separation"):
        validate(now, request, approvals, cb)


def test_audit_failure_rolls_back_nonce_pair_atomically():
    now, request, approvals = fixture()
    cb = callbacks(approvals, audit_ok=False)
    with pytest.raises(DualApprovalError, match="audit"):
        validate(now, request, approvals, cb)
    assert len(cb[-2]) == 1


@pytest.mark.parametrize("legacy_name", ["nonce_pair_consumer", "audit_append"])
def test_legacy_split_callbacks_are_rejected_before_any_callback(legacy_name):
    now, request, approvals = fixture()
    calls = []

    def forbidden(*args, **kwargs):
        calls.append(True)
        raise AssertionError("split callback must never be invoked")

    kwargs = {
        "signature_verifier": forbidden,
        "identity_verifier": forbidden,
        "atomic_pair_audit_commit": forbidden,
        legacy_name: forbidden,
        "now": now,
    }
    with pytest.raises(DualApprovalError, match="Separate nonce and audit callbacks are prohibited"):
        validate_dual_approval(request, approvals, **kwargs)
    assert calls == []

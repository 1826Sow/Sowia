"""Offline dual-approval policy gate for FINAL TEC.

This module verifies two independent approval envelopes over one immutable
request digest. Trust, identity, signature verification, atomic nonce-pair
consumption, and append-only audit are injected interfaces. It never executes
a workload and never grants execution authorization.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Sequence

import rfc8785


class DualApprovalError(ValueError):
    """Raised when the dual-approval gate must fail closed."""


_APPROVAL_FIELDS = {
    "subject_id", "role", "key_id", "algorithm", "approval_policy_id",
    "policy_version", "nonce", "issued_at", "expires_at", "signature",
}
_REQUEST_FIELDS = {
    "authorization_id", "request_version", "requester_id", "operator_id",
    "reviewer_id", "policy_version", "expires_at", "environment_digest",
    "constraints_digest", "action_digest",
}


def _timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise DualApprovalError(f"{field}: ISO-8601 timestamp required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DualApprovalError(f"{field}: invalid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise DualApprovalError(f"{field}: timezone required")
    return parsed.astimezone(timezone.utc)


def _nonempty(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DualApprovalError(f"{field}: non-empty string required")
    return value


def _sha256_digest(value: Any, field: str) -> str:
    digest = _nonempty(value, field)
    if len(digest) != 64:
        raise DualApprovalError(f"{field}: 64-character SHA-256 hex digest required")
    if any(character not in "0123456789abcdefABCDEF" for character in digest):
        raise DualApprovalError(f"{field}: invalid SHA-256 hex digest")
    return digest.lower()


def request_digest(request: Mapping[str, Any]) -> str:
    """Return SHA-256 over the RFC 8785 canonical request representation."""
    try:
        canonical = rfc8785.dumps(dict(request))
    except (TypeError, ValueError) as exc:
        raise DualApprovalError("Request is not valid RFC 8785 JSON") from exc
    return hashlib.sha256(canonical).hexdigest()


def _signed_envelope(request: Mapping[str, Any], digest: str, approval: Mapping[str, Any]) -> dict[str, Any]:
    unsigned_approval = {key: value for key, value in approval.items() if key != "signature"}
    return {"request": dict(request), "request_digest": digest, "approval": unsigned_approval}


def validate_dual_approval(
    request: Mapping[str, Any],
    approvals: Sequence[Mapping[str, Any]],
    *,
    signature_verifier: Callable[[Mapping[str, Any], Mapping[str, Any]], bool],
    identity_verifier: Callable[[str, str, Mapping[str, Any]], bool],
    nonce_pair_consumer: Callable[[str, Sequence[tuple[str, str]]], bool] | None = None,
    audit_append: Callable[[Mapping[str, Any]], bool] | None = None,
    atomic_pair_audit_commit: Callable[[str, Sequence[tuple[str, str]], Mapping[str, Any]], bool] | None = None,
    now: datetime | None = None,
    required_role: str = "security-approver",
) -> dict[str, Any]:
    """Validate two approvals and consume both nonces with one audit transaction.

    The legacy split callbacks remain in the signature only to fail explicitly
    for old callers. They are never invoked or accepted. Trust callbacks must
    use independent authoritative sources.
    """
    if nonce_pair_consumer is not None or audit_append is not None:
        raise DualApprovalError(
            "Separate nonce and audit callbacks are prohibited; use atomic_pair_audit_commit"
        )
    if not isinstance(request, Mapping) or set(request) != _REQUEST_FIELDS:
        raise DualApprovalError("Request fields are incomplete or unexpected")
    if not isinstance(approvals, Sequence) or isinstance(approvals, (str, bytes)) or len(approvals) != 2:
        raise DualApprovalError("Exactly two approval records are required")

    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None or current.utcoffset() is None:
        raise DualApprovalError("Clock must be timezone-aware")
    current = current.astimezone(timezone.utc)

    for field in _REQUEST_FIELDS:
        _nonempty(request[field], f"request.{field}")
    for field in ("environment_digest", "constraints_digest", "action_digest"):
        _sha256_digest(request[field], f"request.{field}")
    if request["requester_id"] in {request["operator_id"], request["reviewer_id"]}:
        raise DualApprovalError("Requester must be distinct from operator and reviewer")
    if request["operator_id"] == request["reviewer_id"]:
        raise DualApprovalError("Operator and reviewer must be distinct")

    request_expiry = _timestamp(request["expires_at"], "request.expires_at")
    if request_expiry <= current:
        raise DualApprovalError("Request expired")
    digest = request_digest(request)

    # Reject duplicate identities/keys/nonces before invoking any external
    # trust callback, so callback order cannot mask a pair-level violation.
    for field in ("subject_id", "key_id", "nonce"):
        values = [
            _nonempty(item.get(field), f"approvals[{index}].{field}")
            if isinstance(item, Mapping) else ""
            for index, item in enumerate(approvals)
        ]
        if len(set(values)) != 2:
            raise DualApprovalError(f"Both approvals must use distinct {field} values")

    # Both signatures must be issued under the same approval policy. Check
    # this pair-level invariant before invoking any trust callback.
    policy_ids = [
        _nonempty(item.get("approval_policy_id"), f"approvals[{index}].approval_policy_id")
        if isinstance(item, Mapping) else ""
        for index, item in enumerate(approvals)
    ]
    if policy_ids[0] != policy_ids[1]:
        raise DualApprovalError("Both approvals must use the same approval_policy_id")

    normalized: list[dict[str, Any]] = []
    subjects: set[str] = set()
    key_ids: set[str] = set()
    nonces: set[str] = set()
    nonce_records: list[tuple[str, str]] = []

    for index, approval in enumerate(approvals):
        prefix = f"approvals[{index}]"
        if not isinstance(approval, Mapping) or set(approval) != _APPROVAL_FIELDS:
            raise DualApprovalError(f"{prefix}: approval fields incomplete or unexpected")

        subject = _nonempty(approval["subject_id"], f"{prefix}.subject_id")
        role = _nonempty(approval["role"], f"{prefix}.role")
        key_id = _nonempty(approval["key_id"], f"{prefix}.key_id")
        policy_version = _nonempty(approval["policy_version"], f"{prefix}.policy_version")
        _nonempty(approval["approval_policy_id"], f"{prefix}.approval_policy_id")
        nonce = _nonempty(approval["nonce"], f"{prefix}.nonce")
        _nonempty(approval["signature"], f"{prefix}.signature")

        if role != required_role:
            raise DualApprovalError(f"{prefix}: required approver role missing")
        if policy_version != request["policy_version"]:
            raise DualApprovalError(f"{prefix}: policy version mismatch")
        if approval["algorithm"] != "Ed25519":
            raise DualApprovalError(f"{prefix}: unsupported signature algorithm")
        if len(nonce) < 32 or len(nonce) > 256:
            raise DualApprovalError(f"{prefix}: nonce length outside policy")
        if subject in subjects or key_id in key_ids or nonce in nonces:
            raise DualApprovalError("Approvers, keys, and nonces must be distinct")
        if subject in {request["requester_id"], request["operator_id"], request["reviewer_id"]}:
            raise DualApprovalError("Approver role separation violation")

        issued = _timestamp(approval["issued_at"], f"{prefix}.issued_at")
        expires = _timestamp(approval["expires_at"], f"{prefix}.expires_at")
        if issued > current or expires <= current or expires <= issued:
            raise DualApprovalError(f"{prefix}: approval outside validity window")
        if expires > request_expiry:
            raise DualApprovalError(f"{prefix}: approval outlives request")

        signed = _signed_envelope(request, digest, approval)
        identity_context = {"approval": dict(approval), "request_digest": digest}
        # Verify the approval's Ed25519 signature before consuming the
        # one-time OIDC approval session. Otherwise an invalid signature could
        # burn a valid session and prevent a legitimate retry.
        if signature_verifier(signed, approval) is not True:
            raise DualApprovalError(f"{prefix}: signature or trusted key invalid")
        if identity_verifier(subject, role, identity_context) is not True:
            raise DualApprovalError(f"{prefix}: identity or role not independently verified")

        subjects.add(subject)
        key_ids.add(key_id)
        nonces.add(nonce)
        nonce_records.append((nonce, expires.isoformat()))
        normalized.append({
            "subject_id": subject, "key_id": key_id, "role": role,
            "request_digest": digest, "issued_at": issued.isoformat(),
            "expires_at": expires.isoformat(),
        })

    audit_event = {
        "event_type": "dual_approval_verified",
        "authorization_id": request["authorization_id"],
        "request_version": request["request_version"],
        "request_digest": digest,
        "approvals": normalized,
        "occurred_at": current.isoformat(),
        "execution_authorized": False,
    }

    if atomic_pair_audit_commit is None:
        raise DualApprovalError("Atomic pair/audit commit callback is required")
    if atomic_pair_audit_commit(
        request["authorization_id"], tuple(nonce_records), audit_event
    ) is not True:
        raise DualApprovalError("Atomic nonce-pair and audit commit unavailable")

    return {
        "authorization_id": request["authorization_id"],
        "request_digest": digest,
        "approval_result": "dual_approval_verified_not_execution_authorized",
        "approver_count": 2,
        "distinct_approvers": True,
        "signatures_verified": True,
        "identities_verified_by_injected_authority": True,
        "nonce_pair_consumed_atomically": True,
        "audit_appended": True,
        "nonce_pair_and_audit_committed_atomically": True,
        "execution_authorized": False,
        "workload_executed": False,
        "g2b_status": "NO-GO / NOT_RUN",
    }

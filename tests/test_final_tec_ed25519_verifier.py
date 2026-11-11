from base64 import b64encode
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from final_tec_ed25519_verifier import (
    Ed25519ApprovalVerifier,
    TrustedApprovalKey,
)


def build_case(*, issued_at=None, signing_disabled_at=None):
    now = datetime.now(timezone.utc)
    private = Ed25519PrivateKey.generate()
    public_raw = private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    payload = {
        "actors": {"approver_id": "approver-a"},
        "issued_at": issued_at or (now - timedelta(seconds=10)).isoformat(),
        "authorization_id": "authorization-a",
    }
    record = TrustedApprovalKey(
        key_id="key-a",
        approver_id="approver-a",
        approver_role="security-approver",
        public_key_raw=public_raw,
        valid_from=now - timedelta(days=1),
        valid_until=now + timedelta(days=1),
        signing_disabled_at=signing_disabled_at,
    )
    verifier = Ed25519ApprovalVerifier({"key-a": record})
    signature = private.sign(verifier.canonical_payload(payload))
    approval = {
        "algorithm": "Ed25519",
        "key_id": "key-a",
        "approver_role": "security-approver",
        "signature": b64encode(signature).decode("ascii"),
    }
    return now, payload, approval, verifier


def test_valid_trusted_ed25519_signature_is_accepted():
    _, payload, approval, verifier = build_case()
    assert verifier(payload, approval) is True


def test_disabled_key_rejects_backdated_signature_without_trusted_timestamp():
    now = datetime.now(timezone.utc)
    _, payload, approval, verifier = build_case(
        signing_disabled_at=now - timedelta(seconds=1)
    )
    assert verifier(payload, approval) is False


def test_naive_signed_timestamp_is_rejected():
    _, payload, approval, verifier = build_case(issued_at="2026-01-01T12:00:00")
    assert verifier(payload, approval) is False

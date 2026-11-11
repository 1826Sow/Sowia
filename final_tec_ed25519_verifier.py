"""Trusted Ed25519 approval verification for FINAL TEC's offline contract gate.

This module verifies signatures only. Trust records must be provisioned from an
independent, authenticated source; a key included in the submitted contract is
never trusted. It does not authenticate a human identity by itself.
"""
from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

import rfc8785
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


class ApprovalVerificationError(ValueError):
    """Raised when a trusted-key or Ed25519 verification check fails."""


def _utc(value: datetime, field: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ApprovalVerificationError(f"{field}: timezone-aware datetime required")
    return value.astimezone(timezone.utc)


@dataclass(frozen=True)
class TrustedApprovalKey:
    key_id: str
    approver_id: str
    approver_role: str
    public_key_raw: bytes
    valid_from: datetime
    valid_until: datetime
    revoked_at: datetime | None = None
    signing_disabled_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.key_id or not self.approver_id or not self.approver_role:
            raise ValueError("key_id, approver_id and approver_role are required")
        if not isinstance(self.public_key_raw, bytes) or len(self.public_key_raw) != 32:
            raise ValueError("Ed25519 public key must contain exactly 32 raw bytes")
        start = _utc(self.valid_from, "valid_from")
        end = _utc(self.valid_until, "valid_until")
        if end <= start:
            raise ValueError("valid_until must be later than valid_from")
        if self.revoked_at is not None:
            _utc(self.revoked_at, "revoked_at")
        if self.signing_disabled_at is not None:
            _utc(self.signing_disabled_at, "signing_disabled_at")


class Ed25519ApprovalVerifier:
    """Callable verifier compatible with validate_authorization_contract.

    The registry is an explicit trusted input, not data from the approval
    envelope. Multiple key IDs allow planned rotation; old keys can remain
    verification-only by setting signing_disabled_at while retaining validity.
    Revocation is immediate and rejects signatures regardless of issue date.
    """

    def __init__(self, trusted_keys: Mapping[str, TrustedApprovalKey]):
        copied = dict(trusted_keys)
        for key_id, record in copied.items():
            if key_id != record.key_id:
                raise ValueError("trusted key mapping key does not match record.key_id")
        self._trusted_keys = copied

    @staticmethod
    def canonical_payload(payload: Mapping[str, Any]) -> bytes:
        try:
            return rfc8785.dumps(dict(payload))
        except (TypeError, ValueError) as exc:
            raise ApprovalVerificationError("Payload is not valid RFC 8785 JSON") from exc

    def verify_identity(self, approver_id: str, approver_role: str) -> bool:
        # Identity is bound to an explicitly trusted key record. An external
        # identity provider is still required to establish the real person.
        return any(
            key.approver_id == approver_id and key.approver_role == approver_role
            for key in self._trusted_keys.values()
        )

    def __call__(self, payload: Mapping[str, Any], approval: Mapping[str, Any]) -> bool:
        if approval.get("algorithm") != "Ed25519":
            return False
        key_id = approval.get("key_id")
        if not isinstance(key_id, str):
            return False
        record = self._trusted_keys.get(key_id)
        if record is None:
            return False

        approver_id = payload.get("actors", {}).get("approver_id")
        if approver_id != record.approver_id:
            return False
        if approval.get("approver_role") != record.approver_role:
            return False

        try:
            issued_at = _utc(
                datetime.fromisoformat(str(payload["issued_at"]).replace("Z", "+00:00")),
                "issued_at",
            )
            now = datetime.now(timezone.utc)
            valid_from = _utc(record.valid_from, "valid_from")
            valid_until = _utc(record.valid_until, "valid_until")
            if issued_at < valid_from or issued_at > valid_until:
                return False
            if now < valid_from or now > valid_until:
                return False
            if record.revoked_at is not None and now >= _utc(record.revoked_at, "revoked_at"):
                return False
            # A signed issued_at value is not an independent trusted
            # timestamp. Once signing is disabled, reject all verification
            # rather than accepting potentially backdated signatures.
            if record.signing_disabled_at is not None and now >= _utc(
                record.signing_disabled_at, "signing_disabled_at"
            ):
                return False

            encoded = approval.get("signature")
            if not isinstance(encoded, str):
                return False
            signature = base64.b64decode(encoded, validate=True)
            if len(signature) != 64:
                return False
            public_key = Ed25519PublicKey.from_public_bytes(record.public_key_raw)
            public_key.verify(signature, self.canonical_payload(payload))
            return True
        except (KeyError, TypeError, ValueError, binascii.Error, InvalidSignature):
            return False

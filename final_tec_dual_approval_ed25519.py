"""Ed25519 trust adapter for FINAL TEC dual approvals.

This verifies cryptographic signatures against independently supplied public-key
records. It does NOT authenticate a human; the identity_verifier callback must
still query an authoritative identity provider and current role assignment.
"""
from __future__ import annotations

import base64
import binascii
from datetime import datetime, timezone
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
import rfc8785

from final_tec_ed25519_verifier import TrustedApprovalKey


class DualApprovalEd25519Verifier:
    """Callable signature_verifier for validate_dual_approval."""

    def __init__(self, trusted_keys: Mapping[str, TrustedApprovalKey]):
        self._keys = dict(trusted_keys)
        for key_id, record in self._keys.items():
            if key_id != record.key_id:
                raise ValueError("Trusted key map key must match record.key_id")

    @staticmethod
    def canonical_payload(envelope: Mapping[str, Any]) -> bytes:
        try:
            return rfc8785.dumps(dict(envelope))
        except (TypeError, ValueError) as exc:
            raise ValueError("Dual approval envelope is not RFC 8785 JSON") from exc

    def __call__(self, envelope: Mapping[str, Any], approval: Mapping[str, Any]) -> bool:
        if not isinstance(envelope, Mapping) or not isinstance(approval, Mapping):
            return False
        if approval.get("algorithm") != "Ed25519":
            return False

        key_id = approval.get("key_id")
        if not isinstance(key_id, str):
            return False
        record = self._keys.get(key_id)
        if record is None:
            return False
        if approval.get("subject_id") != record.approver_id:
            return False
        if approval.get("role") != record.approver_role:
            return False

        try:
            issued_at = datetime.fromisoformat(
                str(approval["issued_at"]).replace("Z", "+00:00")
            )
            if issued_at.tzinfo is None or issued_at.utcoffset() is None:
                return False
            issued_at = issued_at.astimezone(timezone.utc)
            now = datetime.now(timezone.utc)
            valid_from = record.valid_from.astimezone(timezone.utc)
            valid_until = record.valid_until.astimezone(timezone.utc)

            if not valid_from <= issued_at <= valid_until:
                return False
            if not valid_from <= now <= valid_until:
                return False
            if record.revoked_at is not None and now >= record.revoked_at.astimezone(timezone.utc):
                return False
            # A caller-supplied signed timestamp is not an independent
            # trusted timestamp. Once signing is disabled, fail closed for
            # every verification; do not accept backdated signatures.
            if record.signing_disabled_at is not None and now >= record.signing_disabled_at.astimezone(timezone.utc):
                return False

            encoded = approval.get("signature")
            if not isinstance(encoded, str):
                return False
            signature = base64.b64decode(encoded, validate=True)
            if len(signature) != 64:
                return False
            public_key = Ed25519PublicKey.from_public_bytes(record.public_key_raw)
            public_key.verify(signature, self.canonical_payload(envelope))
            return True
        except (
            KeyError, TypeError, ValueError, binascii.Error, InvalidSignature
        ):
            return False

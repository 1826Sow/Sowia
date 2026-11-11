"""Fail-closed coordinator for transactional audit outbox + external anchoring.

The ledger must atomically consume both nonces, append the audit event, and
persist an anchor-pending outbox checkpoint. The coordinator returns success
only after the external receipt is verified and the ledger durably marks the
checkpoint anchored. Provider implementations are injected.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Mapping, Protocol, Sequence


@dataclass(frozen=True)
class AuditCheckpoint:
    authorization_id: str
    sequence: int
    previous_hash: str
    event_hash: str
    created_at_utc: str


class TransactionalAuditOutbox(Protocol):
    """Ledger-side contract; the first method must be one DB transaction."""

    def commit_pair_audit_and_outbox(
        self,
        authorization_id: str,
        nonce_records: Sequence[tuple[str, str]],
        audit_event: Mapping[str, Any],
    ) -> AuditCheckpoint | None: ...

    def mark_checkpoint_anchored(
        self,
        authorization_id: str,
        event_hash: str,
        receipt: Mapping[str, str],
    ) -> bool: ...


class ExternalCheckpointAnchor(Protocol):
    """Append must be idempotent for an identical checkpoint tuple."""

    def append_checkpoint(
        self,
        sequence: int,
        previous_hash: str,
        event_hash: str,
        created_at_utc: str,
    ) -> Mapping[str, str]: ...

    def verify_checkpoint(
        self,
        sequence: int,
        previous_hash: str,
        event_hash: str,
        created_at_utc: str,
        receipt: Mapping[str, str],
    ) -> bool: ...


def _valid_checkpoint(checkpoint: Any, authorization_id: str) -> bool:
    if not isinstance(checkpoint, AuditCheckpoint):
        return False
    if checkpoint.authorization_id != authorization_id:
        return False
    if not isinstance(checkpoint.sequence, int) or isinstance(checkpoint.sequence, bool) or checkpoint.sequence < 1:
        return False
    for value in (checkpoint.previous_hash, checkpoint.event_hash):
        if not isinstance(value, str) or len(value) != 64:
            return False
        try:
            int(value, 16)
        except ValueError:
            return False
    if not isinstance(checkpoint.created_at_utc, str):
        return False
    try:
        parsed = datetime.fromisoformat(checkpoint.created_at_utc.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


class ExternalAuditAnchorCoordinator:
    """Callback adapter: no success until a durable, verified anchor receipt."""

    def __init__(self, ledger: TransactionalAuditOutbox, anchor: ExternalCheckpointAnchor):
        self.ledger = ledger
        self.anchor = anchor

    def commit_and_anchor(
        self,
        authorization_id: str,
        nonce_records: Sequence[tuple[str, str]],
        audit_event: Mapping[str, Any],
    ) -> bool:
        if not isinstance(authorization_id, str) or not authorization_id.strip():
            return False
        try:
            checkpoint = self.ledger.commit_pair_audit_and_outbox(
                authorization_id, nonce_records, audit_event
            )
            if not _valid_checkpoint(checkpoint, authorization_id):
                return False
            receipt = self.anchor.append_checkpoint(
                checkpoint.sequence,
                checkpoint.previous_hash,
                checkpoint.event_hash,
                checkpoint.created_at_utc,
            )
            if not isinstance(receipt, Mapping) or not receipt:
                return False
            if any(
                not isinstance(key, str) or not key.strip()
                or not isinstance(value, str) or not value.strip()
                for key, value in receipt.items()
            ):
                return False
            if self.anchor.verify_checkpoint(
                checkpoint.sequence,
                checkpoint.previous_hash,
                checkpoint.event_hash,
                checkpoint.created_at_utc,
                receipt,
            ) is not True:
                return False
            return self.ledger.mark_checkpoint_anchored(
                authorization_id, checkpoint.event_hash, dict(receipt)
            ) is True
        except Exception:
            # Do not leak provider exception details into caller-visible output.
            return False

    def callback(self) -> Callable[
        [str, Sequence[tuple[str, str]], Mapping[str, Any]], bool
    ]:
        """Return the signature expected by validate_dual_approval."""
        return self.commit_and_anchor

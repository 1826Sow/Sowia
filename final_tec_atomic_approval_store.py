"""Single-host SQLite store for atomic dual-nonce consumption + audit.

The two nonce state changes and the tamper-evident audit append are committed in
one SQLite transaction. This is a local reference implementation, not a
distributed consensus store or a privileged-admin-proof immutable ledger.
"""
from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import rfc8785


class AtomicApprovalStoreError(ValueError):
    """Raised when the local atomic approval store cannot safely proceed."""


def _epoch(value: datetime, field: str) -> float:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise AtomicApprovalStoreError(f"{field} must be timezone-aware")
    result = value.astimezone(timezone.utc).timestamp()
    if not math.isfinite(result):
        raise AtomicApprovalStoreError(f"{field} must be finite")
    return result


def _parse_expiry(value: str) -> float:
    if not isinstance(value, str):
        raise AtomicApprovalStoreError("nonce expiry must be an ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AtomicApprovalStoreError("nonce expiry is invalid") from exc
    return _epoch(parsed, "nonce expiry")


def _nonce_digest(value: str) -> str:
    if not isinstance(value, str) or not 32 <= len(value) <= 256:
        raise AtomicApprovalStoreError("nonce must contain 32 to 256 characters")
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_json(value: Mapping[str, Any]) -> bytes:
    try:
        return rfc8785.dumps(dict(value))
    except (TypeError, ValueError) as exc:
        raise AtomicApprovalStoreError("audit event is not RFC 8785 JSON") from exc


class SQLiteAtomicApprovalStore:
    """Atomic pair registry and append-only, hash-chained audit log.

    Use only on a validated local filesystem on one host. Do not share this
    SQLite file between hosts or place it on an unvalidated network filesystem.
    """

    def __init__(self, database_path: str | Path, *, timeout_seconds: float = 15.0):
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise AtomicApprovalStoreError("timeout_seconds must be positive and finite")
        self.database_path = str(database_path)
        self.timeout_seconds = timeout_seconds
        if self.database_path != ":memory:":
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.database_path,
            timeout=self.timeout_seconds,
            isolation_level=None,
        )
        connection.execute(f"PRAGMA busy_timeout = {int(self.timeout_seconds * 1000)}")
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA synchronous = FULL")
        return connection

    def _initialize(self) -> None:
        connection = self._connect()
        try:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS dual_approval_nonces (
                    nonce_digest TEXT PRIMARY KEY,
                    authorization_id TEXT NOT NULL,
                    expires_at REAL NOT NULL,
                    revoked_at REAL,
                    consumed_at REAL
                );

                CREATE INDEX IF NOT EXISTS idx_dual_approval_nonces_auth
                ON dual_approval_nonces(authorization_id);

                CREATE TABLE IF NOT EXISTS dual_approval_audit (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_json TEXT NOT NULL,
                    previous_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL UNIQUE,
                    created_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS dual_approval_anchor_outbox (
                    authorization_id TEXT PRIMARY KEY,
                    sequence INTEGER NOT NULL UNIQUE
                        REFERENCES dual_approval_audit(sequence),
                    previous_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL UNIQUE,
                    created_at REAL NOT NULL,
                    event_json TEXT NOT NULL,
                    nonce_digests_json TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'anchored')),
                    receipt_json TEXT,
                    CHECK (
                        (status = 'pending' AND receipt_json IS NULL)
                        OR (status = 'anchored' AND receipt_json IS NOT NULL)
                    )
                );

                CREATE INDEX IF NOT EXISTS idx_anchor_outbox_status_sequence
                ON dual_approval_anchor_outbox(status, sequence);

                CREATE TRIGGER IF NOT EXISTS anchor_outbox_immutable_fields
                BEFORE UPDATE ON dual_approval_anchor_outbox
                WHEN
                    OLD.authorization_id != NEW.authorization_id
                    OR OLD.sequence != NEW.sequence
                    OR OLD.previous_hash != NEW.previous_hash
                    OR OLD.event_hash != NEW.event_hash
                    OR OLD.created_at != NEW.created_at
                    OR OLD.event_json != NEW.event_json
                    OR OLD.nonce_digests_json != NEW.nonce_digests_json
                    OR OLD.status = 'anchored'
                    OR NOT (OLD.status = 'pending' AND NEW.status = 'anchored')
                BEGIN
                    SELECT RAISE(ABORT, 'anchor outbox transition is immutable');
                END;

                CREATE TRIGGER IF NOT EXISTS anchor_outbox_no_delete
                BEFORE DELETE ON dual_approval_anchor_outbox
                BEGIN
                    SELECT RAISE(ABORT, 'anchor outbox rows are append-only');
                END;

                CREATE TRIGGER IF NOT EXISTS dual_approval_audit_no_update
                BEFORE UPDATE ON dual_approval_audit
                BEGIN
                    SELECT RAISE(ABORT, 'audit rows are append-only');
                END;

                CREATE TRIGGER IF NOT EXISTS dual_approval_audit_no_delete
                BEFORE DELETE ON dual_approval_audit
                BEGIN
                    SELECT RAISE(ABORT, 'audit rows are append-only');
                END;
            """)
        finally:
            connection.close()

    def register_pair(
        self,
        authorization_id: str,
        records: Sequence[tuple[str, str]],
        *,
        now: datetime | None = None,
    ) -> bool:
        """Register exactly two nonce/expiry pairs in one transaction."""
        if not isinstance(authorization_id, str) or not authorization_id.strip():
            raise AtomicApprovalStoreError("authorization_id is required")
        if len(records) != 2:
            raise AtomicApprovalStoreError("exactly two nonce records are required")
        current = _epoch(now or datetime.now(timezone.utc), "now")
        prepared = []
        for nonce, expiry_text in records:
            digest = _nonce_digest(nonce)
            expiry = _parse_expiry(expiry_text)
            if expiry <= current:
                raise AtomicApprovalStoreError("nonce expiry must be in the future")
            prepared.append((digest, authorization_id, expiry))
        if prepared[0][0] == prepared[1][0]:
            raise AtomicApprovalStoreError("nonce pair must be distinct")

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            for row in prepared:
                cursor = connection.execute(
                    """INSERT OR IGNORE INTO dual_approval_nonces
                       (nonce_digest, authorization_id, expires_at)
                       VALUES (?, ?, ?)""",
                    row,
                )
                if cursor.rowcount != 1:
                    connection.rollback()
                    return False
            connection.commit()
            return True
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def revoke(self, nonce: str, *, now: datetime | None = None) -> bool:
        digest = _nonce_digest(nonce)
        current = _epoch(now or datetime.now(timezone.utc), "now")
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                """UPDATE dual_approval_nonces SET revoked_at = ?
                   WHERE nonce_digest = ? AND revoked_at IS NULL AND consumed_at IS NULL""",
                (current, digest),
            )
            connection.commit()
            return cursor.rowcount == 1
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def commit_pair_and_audit(
        self,
        authorization_id: str,
        records: Sequence[tuple[str, str]],
        audit_event: Mapping[str, Any],
        *,
        now: datetime | None = None,
    ) -> bool:
        """Consume both registered nonces and append audit atomically.

        Returns False without changing either nonce when either record is
        missing, mismatched, expired, revoked, consumed, or when the audit
        append cannot complete.
        """
        if not isinstance(authorization_id, str) or not authorization_id.strip():
            return False
        if len(records) != 2:
            return False
        current = _epoch(now or datetime.now(timezone.utc), "now")
        try:
            prepared = [(_nonce_digest(nonce), _parse_expiry(expiry)) for nonce, expiry in records]
            if prepared[0][0] == prepared[1][0]:
                return False
            event_bytes = _canonical_json(audit_event)
            event_text = event_bytes.decode("utf-8")
        except (AtomicApprovalStoreError, UnicodeDecodeError):
            return False

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            for digest, requested_expiry in prepared:
                row = connection.execute(
                    """SELECT expires_at, revoked_at, consumed_at
                       FROM dual_approval_nonces
                       WHERE nonce_digest = ? AND authorization_id = ?""",
                    (digest, authorization_id),
                ).fetchone()
                if row is None:
                    connection.rollback()
                    return False
                stored_expiry, revoked_at, consumed_at = row
                if (
                    not math.isclose(stored_expiry, requested_expiry, rel_tol=0, abs_tol=0.000001)
                    or stored_expiry <= current
                    or revoked_at is not None
                    or consumed_at is not None
                ):
                    connection.rollback()
                    return False

            previous = connection.execute(
                "SELECT event_hash FROM dual_approval_audit ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
            previous_hash = previous[0] if previous else "0" * 64
            event_hash = hashlib.sha256(
                previous_hash.encode("ascii") + event_bytes
            ).hexdigest()

            for digest, _ in prepared:
                cursor = connection.execute(
                    """UPDATE dual_approval_nonces SET consumed_at = ?
                       WHERE nonce_digest = ? AND authorization_id = ?
                         AND consumed_at IS NULL AND revoked_at IS NULL AND expires_at > ?""",
                    (current, digest, authorization_id, current),
                )
                if cursor.rowcount != 1:
                    connection.rollback()
                    return False

            connection.execute(
                """INSERT INTO dual_approval_audit
                   (event_json, previous_hash, event_hash, created_at)
                   VALUES (?, ?, ?, ?)""",
                (event_text, previous_hash, event_hash, current),
            )
            connection.commit()
            return True
        except (sqlite3.Error, AtomicApprovalStoreError):
            connection.rollback()
            return False
        finally:
            connection.close()

    def commit_pair_audit_and_outbox(
        self,
        authorization_id: str,
        records: Sequence[tuple[str, str]],
        audit_event: Mapping[str, Any],
        *,
        now: datetime | None = None,
    ):
        """Atomically consume both nonces, append audit, and persist anchor outbox.

        An exact retry returns the original checkpoint without consuming the
        nonces again. Reuse of an authorization ID with different event or
        nonce digests fails closed.
        """
        from final_tec_audit_anchor import AuditCheckpoint

        if not isinstance(authorization_id, str) or not authorization_id.strip():
            return None
        if len(records) != 2:
            return None
        try:
            current = _epoch(now or datetime.now(timezone.utc), "now")
            prepared = [(_nonce_digest(nonce), _parse_expiry(expiry)) for nonce, expiry in records]
            if prepared[0][0] == prepared[1][0]:
                return None
            event_bytes = _canonical_json(audit_event)
            event_text = event_bytes.decode("utf-8")
            nonce_digests_json = json.dumps(
                sorted([[digest, expiry] for digest, expiry in prepared]),
                separators=(",", ":"),
            )
        except (AtomicApprovalStoreError, UnicodeDecodeError):
            return None

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")

            existing = connection.execute(
                """SELECT sequence, previous_hash, event_hash, created_at,
                          event_json, nonce_digests_json
                   FROM dual_approval_anchor_outbox WHERE authorization_id = ?""",
                (authorization_id,),
            ).fetchone()
            if existing is not None:
                sequence, previous_hash, event_hash, created_at, stored_event, stored_nonces = existing
                if stored_event != event_text or stored_nonces != nonce_digests_json:
                    connection.rollback()
                    return None
                connection.commit()
                return AuditCheckpoint(
                    authorization_id, sequence, previous_hash, event_hash,
                    datetime.fromtimestamp(created_at, timezone.utc).isoformat(),
                )

            for digest, requested_expiry in prepared:
                row = connection.execute(
                    """SELECT expires_at, revoked_at, consumed_at
                       FROM dual_approval_nonces
                       WHERE nonce_digest = ? AND authorization_id = ?""",
                    (digest, authorization_id),
                ).fetchone()
                if row is None:
                    connection.rollback()
                    return None
                stored_expiry, revoked_at, consumed_at = row
                if (
                    not math.isclose(stored_expiry, requested_expiry, rel_tol=0, abs_tol=0.000001)
                    or stored_expiry <= current
                    or revoked_at is not None
                    or consumed_at is not None
                ):
                    connection.rollback()
                    return None

            previous = connection.execute(
                "SELECT event_hash FROM dual_approval_audit ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
            previous_hash = previous[0] if previous else "0" * 64
            event_hash = hashlib.sha256(
                previous_hash.encode("ascii") + event_bytes
            ).hexdigest()

            for digest, _ in prepared:
                cursor = connection.execute(
                    """UPDATE dual_approval_nonces SET consumed_at = ?
                       WHERE nonce_digest = ? AND authorization_id = ?
                         AND consumed_at IS NULL AND revoked_at IS NULL AND expires_at > ?""",
                    (current, digest, authorization_id, current),
                )
                if cursor.rowcount != 1:
                    connection.rollback()
                    return None

            audit_cursor = connection.execute(
                """INSERT INTO dual_approval_audit
                   (event_json, previous_hash, event_hash, created_at)
                   VALUES (?, ?, ?, ?)""",
                (event_text, previous_hash, event_hash, current),
            )
            sequence = audit_cursor.lastrowid
            connection.execute(
                """INSERT INTO dual_approval_anchor_outbox
                   (authorization_id, sequence, previous_hash, event_hash,
                    created_at, event_json, nonce_digests_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (authorization_id, sequence, previous_hash, event_hash,
                 current, event_text, nonce_digests_json),
            )
            connection.commit()
            return AuditCheckpoint(
                authorization_id, sequence, previous_hash, event_hash,
                datetime.fromtimestamp(current, timezone.utc).isoformat(),
            )
        except (sqlite3.Error, AtomicApprovalStoreError):
            connection.rollback()
            return None
        finally:
            connection.close()

    def mark_checkpoint_anchored(
        self,
        authorization_id: str,
        event_hash: str,
        receipt: Mapping[str, str],
    ) -> bool:
        """Persist a verified external receipt; only pending -> anchored is allowed."""
        if not isinstance(authorization_id, str) or not authorization_id.strip():
            return False
        if not isinstance(event_hash, str) or len(event_hash) != 64:
            return False
        try:
            receipt_text = _canonical_json(receipt).decode("utf-8")
        except (AtomicApprovalStoreError, UnicodeDecodeError):
            return False
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """SELECT status, receipt_json FROM dual_approval_anchor_outbox
                   WHERE authorization_id = ? AND event_hash = ?""",
                (authorization_id, event_hash),
            ).fetchone()
            if row is None:
                connection.rollback()
                return False
            status, existing_receipt = row
            if status == "anchored":
                connection.rollback()
                return existing_receipt == receipt_text
            cursor = connection.execute(
                """UPDATE dual_approval_anchor_outbox
                   SET status = 'anchored', receipt_json = ?
                   WHERE authorization_id = ? AND event_hash = ? AND status = 'pending'""",
                (receipt_text, authorization_id, event_hash),
            )
            if cursor.rowcount != 1:
                connection.rollback()
                return False
            connection.commit()
            return True
        except sqlite3.Error:
            connection.rollback()
            return False
        finally:
            connection.close()

    def pending_anchor_checkpoints(self):
        """Return pending outbox entries in sequence order for safe recovery."""
        from final_tec_audit_anchor import AuditCheckpoint

        connection = self._connect()
        try:
            rows = connection.execute(
                """SELECT authorization_id, sequence, previous_hash, event_hash, created_at
                   FROM dual_approval_anchor_outbox
                   WHERE status = 'pending' ORDER BY sequence"""
            ).fetchall()
        finally:
            connection.close()
        return [
            AuditCheckpoint(
                authorization_id, sequence, previous_hash, event_hash,
                datetime.fromtimestamp(created_at, timezone.utc).isoformat(),
            )
            for authorization_id, sequence, previous_hash, event_hash, created_at in rows
        ]

    def anchor_outbox_status(self, authorization_id: str) -> str | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT status FROM dual_approval_anchor_outbox WHERE authorization_id = ?",
                (authorization_id,),
            ).fetchone()
        finally:
            connection.close()
        return row[0] if row else None

    def atomic_commit_callback(self, authorization_id: str, records: Sequence[tuple[str, str]],
                               audit_event: Mapping[str, Any]) -> bool:
        """Callback adapter for validate_dual_approval."""
        return self.commit_pair_and_audit(authorization_id, records, audit_event)

    def audit_events(self) -> list[dict[str, Any]]:
        connection = self._connect()
        try:
            rows = connection.execute(
                """SELECT sequence, event_json, previous_hash, event_hash
                   FROM dual_approval_audit ORDER BY sequence"""
            ).fetchall()
        finally:
            connection.close()
        return [
            {
                "sequence": sequence,
                "event": json.loads(event_json),
                "previous_hash": previous_hash,
                "event_hash": event_hash,
            }
            for sequence, event_json, previous_hash, event_hash in rows
        ]

    def verify_audit_chain(self) -> bool:
        connection = self._connect()
        try:
            rows = connection.execute(
                """SELECT event_json, previous_hash, event_hash
                   FROM dual_approval_audit ORDER BY sequence"""
            ).fetchall()
        finally:
            connection.close()
        previous_hash = "0" * 64
        for event_json, stored_previous, stored_hash in rows:
            if stored_previous != previous_hash:
                return False
            expected = hashlib.sha256(
                previous_hash.encode("ascii") + event_json.encode("utf-8")
            ).hexdigest()
            if expected != stored_hash:
                return False
            previous_hash = stored_hash
        return True

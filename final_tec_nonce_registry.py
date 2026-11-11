"""Single-host SQLite anti-replay registry for FINAL TEC authorization nonces.

This is a local reference implementation, not a distributed or production trust
service. It stores only SHA-256 nonce digests and uses SQLite write transactions
to ensure one successful consumption per registered nonce.
"""
from __future__ import annotations

import hashlib
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class NonceRegistryError(ValueError):
    """Raised when nonce registry input is invalid."""


def _aware_epoch(value: datetime | None, field: str) -> float:
    if value is None:
        value = datetime.now(timezone.utc)
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise NonceRegistryError(f"{field} must be timezone-aware")
    result = value.astimezone(timezone.utc).timestamp()
    if not math.isfinite(result):
        raise NonceRegistryError(f"{field} must be finite")
    return result


def _nonempty(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise NonceRegistryError(f"{field} must be a non-empty string")
    return value


def _nonce_digest(nonce: str) -> str:
    _nonempty(nonce, "nonce")
    if len(nonce) < 32 or len(nonce) > 256:
        raise NonceRegistryError("nonce length must be between 32 and 256 characters")
    return hashlib.sha256(nonce.encode("utf-8")).hexdigest()


class SQLiteNonceRegistry:
    """Atomic single-use nonce store backed by one local SQLite database.

    Each operation opens its own connection. BEGIN IMMEDIATE serializes writers;
    the conditional UPDATE is the final single-use guard. Do not place this
    database on an unvalidated network filesystem or use it across hosts.
    """

    def __init__(self, database_path: str | Path, *, timeout_seconds: float = 10.0):
        self.database_path = str(database_path)
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise NonceRegistryError("timeout_seconds must be positive and finite")
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
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS authorization_nonces (
                    nonce_digest TEXT PRIMARY KEY,
                    authorization_id TEXT NOT NULL,
                    expires_at REAL NOT NULL,
                    revoked_at REAL,
                    consumed_at REAL
                )
            """)
            connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_authorization_nonces_expiry
                ON authorization_nonces(expires_at)
            """)

    def register(
        self,
        nonce: str,
        authorization_id: str,
        expires_at: datetime,
        *,
        now: datetime | None = None,
    ) -> bool:
        """Register a nonce once. Returns False if its digest already exists."""
        digest = _nonce_digest(nonce)
        authorization_id = _nonempty(authorization_id, "authorization_id")
        expiry = _aware_epoch(expires_at, "expires_at")
        current = _aware_epoch(now, "now")
        if expiry <= current:
            raise NonceRegistryError("expires_at must be in the future")
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                """INSERT OR IGNORE INTO authorization_nonces
                   (nonce_digest, authorization_id, expires_at)
                   VALUES (?, ?, ?)""",
                (digest, authorization_id, expiry),
            )
            connection.commit()
            return cursor.rowcount == 1
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def consume(
        self,
        nonce: str,
        authorization_id: str,
        *,
        now: datetime | None = None,
    ) -> bool:
        """Atomically consume a valid nonce exactly once."""
        digest = _nonce_digest(nonce)
        authorization_id = _nonempty(authorization_id, "authorization_id")
        current = _aware_epoch(now, "now")
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                """UPDATE authorization_nonces
                   SET consumed_at = ?
                   WHERE nonce_digest = ?
                     AND authorization_id = ?
                     AND expires_at > ?
                     AND revoked_at IS NULL
                     AND consumed_at IS NULL""",
                (current, digest, authorization_id, current),
            )
            connection.commit()
            return cursor.rowcount == 1
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def revoke(
        self,
        nonce: str,
        *,
        now: datetime | None = None,
    ) -> bool:
        """Revoke an unconsumed nonce. Returns False if it cannot be revoked."""
        digest = _nonce_digest(nonce)
        current = _aware_epoch(now, "now")
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                """UPDATE authorization_nonces
                   SET revoked_at = ?
                   WHERE nonce_digest = ?
                     AND revoked_at IS NULL
                     AND consumed_at IS NULL""",
                (current, digest),
            )
            connection.commit()
            return cursor.rowcount == 1
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def consume_callback(self, nonce: str, authorization_id: str) -> bool:
        """Adapter matching the nonce_consumer callback contract in PR #251."""
        return self.consume(nonce, authorization_id)

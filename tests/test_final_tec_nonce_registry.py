from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import sqlite3

import pytest

from final_tec_nonce_registry import NonceRegistryError, SQLiteNonceRegistry


NOW = datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc)
EXPIRY = NOW + timedelta(minutes=30)
NONCE = "n" * 48


def registry(tmp_path):
    return SQLiteNonceRegistry(tmp_path / "nonce-registry.sqlite3")


def test_register_and_consume_once(tmp_path):
    store = registry(tmp_path)
    assert store.register(NONCE, "auth-001", EXPIRY, now=NOW) is True
    assert store.consume(NONCE, "auth-001", now=NOW) is True
    assert store.consume(NONCE, "auth-001", now=NOW) is False


def test_duplicate_registration_does_not_reset_consumption(tmp_path):
    store = registry(tmp_path)
    assert store.register(NONCE, "auth-001", EXPIRY, now=NOW) is True
    assert store.consume(NONCE, "auth-001", now=NOW) is True
    assert store.register(NONCE, "auth-001", EXPIRY, now=NOW) is False
    assert store.consume(NONCE, "auth-001", now=NOW) is False


def test_wrong_authorization_cannot_consume_nonce(tmp_path):
    store = registry(tmp_path)
    store.register(NONCE, "auth-001", EXPIRY, now=NOW)
    assert store.consume(NONCE, "auth-002", now=NOW) is False
    assert store.consume(NONCE, "auth-001", now=NOW) is True


def test_expired_nonce_cannot_be_consumed(tmp_path):
    store = registry(tmp_path)
    store.register(NONCE, "auth-001", EXPIRY, now=NOW)
    assert store.consume(NONCE, "auth-001", now=EXPIRY) is False


def test_revoked_nonce_cannot_be_consumed(tmp_path):
    store = registry(tmp_path)
    store.register(NONCE, "auth-001", EXPIRY, now=NOW)
    assert store.revoke(NONCE, now=NOW) is True
    assert store.consume(NONCE, "auth-001", now=NOW) is False


def test_consumed_nonce_cannot_be_revoked_or_reused(tmp_path):
    store = registry(tmp_path)
    store.register(NONCE, "auth-001", EXPIRY, now=NOW)
    assert store.consume(NONCE, "auth-001", now=NOW) is True
    assert store.revoke(NONCE, now=NOW) is False
    assert store.consume(NONCE, "auth-001", now=NOW) is False


def test_nonce_is_stored_as_digest_not_plaintext(tmp_path):
    path = tmp_path / "nonce-registry.sqlite3"
    store = SQLiteNonceRegistry(path)
    store.register(NONCE, "auth-001", EXPIRY, now=NOW)
    with sqlite3.connect(path) as connection:
        stored = connection.execute(
            "SELECT nonce_digest FROM authorization_nonces"
        ).fetchone()[0]
    assert stored != NONCE
    assert len(stored) == 64


def test_concurrent_consumers_have_exactly_one_winner(tmp_path):
    path = tmp_path / "nonce-registry.sqlite3"
    store = SQLiteNonceRegistry(path, timeout_seconds=15)
    store.register(NONCE, "auth-001", EXPIRY, now=NOW)

    def attempt(_):
        independent_store = SQLiteNonceRegistry(path, timeout_seconds=15)
        return independent_store.consume(NONCE, "auth-001", now=NOW)

    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(attempt, range(12)))
    assert results.count(True) == 1
    assert results.count(False) == 11


def test_registry_survives_reopening(tmp_path):
    path = tmp_path / "nonce-registry.sqlite3"
    SQLiteNonceRegistry(path).register(NONCE, "auth-001", EXPIRY, now=NOW)
    reopened = SQLiteNonceRegistry(path)
    assert reopened.consume(NONCE, "auth-001", now=NOW) is True
    assert SQLiteNonceRegistry(path).consume(NONCE, "auth-001", now=NOW) is False


def test_naive_timestamps_are_rejected(tmp_path):
    store = registry(tmp_path)
    with pytest.raises(NonceRegistryError):
        store.register(NONCE, "auth-001", datetime(2026, 11, 11, 13, 0), now=NOW)


def test_invalid_nonce_is_rejected(tmp_path):
    store = registry(tmp_path)
    with pytest.raises(NonceRegistryError):
        store.register("short", "auth-001", EXPIRY, now=NOW)


def test_callback_adapter_matches_contract(tmp_path):
    store = registry(tmp_path)
    store.register(NONCE, "auth-001", EXPIRY, now=NOW)
    assert store.consume_callback(NONCE, "auth-001") is True

from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import multiprocessing
from datetime import datetime, timedelta, timezone
import sqlite3

import pytest

from final_tec_atomic_approval_store import (
    AtomicApprovalStoreError,
    SQLiteAtomicApprovalStore,
)
from final_tec_dual_approval import validate_dual_approval, DualApprovalError


def _records(now):
    expiry = (now + timedelta(minutes=15)).isoformat()
    return (("a" * 48, expiry), ("b" * 48, expiry))


def _store(tmp_path, name="atomic-approval.sqlite3"):
    return SQLiteAtomicApprovalStore(tmp_path / name, timeout_seconds=20)


def _process_outbox_commit(args):
    store, authorization_id, records, event, now = args
    return store.commit_pair_audit_and_outbox(
        authorization_id, records, event, now=now
    )


def _process_commit_then_exit_without_ack(args):
    """Commit durably, then simulate process death before returning a result."""
    import os

    store, authorization_id, records, event, now = args
    checkpoint = store.commit_pair_audit_and_outbox(
        authorization_id, records, event, now=now
    )
    os._exit(23 if checkpoint is not None else 24)


class _ExitBeforeCommitConnection:
    """Connection proxy that kills its process immediately before SQLite commit."""

    def __init__(self, connection):
        self._connection = connection

    def __getattr__(self, name):
        return getattr(self._connection, name)

    def commit(self):
        import os

        os._exit(25)


class _CrashBeforeCommitStore(SQLiteAtomicApprovalStore):
    def _connect(self):
        return _ExitBeforeCommitConnection(super()._connect())


def _process_exit_before_sqlite_commit(args):
    store_path, authorization_id, records, event, now = args
    store = _CrashBeforeCommitStore(store_path, timeout_seconds=30)
    store.commit_pair_audit_and_outbox(
        authorization_id, records, event, now=now
    )
    # Reaching this line means the expected commit interception did not occur.
    import os

    os._exit(26)


def test_boolean_sqlite_timeout_configuration_is_rejected(tmp_path):
    from final_tec_atomic_approval_store import AtomicApprovalStoreError

    with pytest.raises(AtomicApprovalStoreError):
        SQLiteAtomicApprovalStore(tmp_path / "invalid-timeout.sqlite3", timeout_seconds=True)


def test_pair_registration_and_atomic_commit_append_one_audit(tmp_path):
    now = datetime.now(timezone.utc)
    store = _store(tmp_path)
    records = _records(now)
    assert store.register_pair("auth-01", records, now=now) is True
    event = {"event_type": "dual_approval_verified", "authorization_id": "auth-01"}
    assert store.commit_pair_and_audit("auth-01", records, event, now=now) is True
    assert len(store.audit_events()) == 1
    assert store.verify_audit_chain() is True
    assert store.commit_pair_and_audit("auth-01", records, event, now=now) is False
    assert len(store.audit_events()) == 1


def test_pair_commit_is_all_or_nothing_when_one_nonce_missing(tmp_path):
    now = datetime.now(timezone.utc)
    store = _store(tmp_path)
    records = _records(now)
    assert store.register_pair("auth-02", records[:1] + (("c" * 48, records[1][1]),), now=now)
    assert store.commit_pair_and_audit(
        "auth-02", records, {"event_type": "should_not_commit"}, now=now
    ) is False
    assert store.audit_events() == []
    # The first nonce remains unconsumed because the other member was absent.
    assert store.commit_pair_and_audit(
        "auth-02",
        (records[0], ("c" * 48, records[1][1])),
        {"event_type": "pair_retry"},
        now=now,
    ) is True


def test_revoking_either_member_prevents_both_from_being_consumed(tmp_path):
    now = datetime.now(timezone.utc)
    store = _store(tmp_path)
    records = _records(now)
    assert store.register_pair("auth-03", records, now=now)
    assert store.revoke(records[1][0], now=now)
    assert store.commit_pair_and_audit(
        "auth-03", records, {"event_type": "revoked_pair"}, now=now
    ) is False
    assert store.audit_events() == []
    # The non-revoked partner remains unconsumed; revocation is not a consume.
    assert store.revoke(records[0][0], now=now) is True


def test_audit_insert_failure_rolls_back_both_nonce_consumptions(tmp_path):
    now = datetime.now(timezone.utc)
    path = tmp_path / "rollback.sqlite3"
    store = SQLiteAtomicApprovalStore(path)
    records = _records(now)
    assert store.register_pair("auth-04", records, now=now)
    with sqlite3.connect(path) as connection:
        connection.execute("""
            CREATE TRIGGER reject_audit_insert
            BEFORE INSERT ON dual_approval_audit
            BEGIN
                SELECT RAISE(ABORT, 'injected audit outage');
            END
        """)
    assert store.commit_pair_and_audit(
        "auth-04", records, {"event_type": "must_rollback", "authorization_id": "auth-outbox-03"}, now=now
    ) is False
    assert store.audit_events() == []
    with sqlite3.connect(path) as connection:
        connection.execute("DROP TRIGGER reject_audit_insert")
    assert store.commit_pair_and_audit(
        "auth-04", records, {"event_type": "retry_after_recovery"}, now=now
    ) is True
    assert len(store.audit_events()) == 1


def test_concurrent_pair_commits_have_one_winner_and_one_audit(tmp_path):
    now = datetime.now(timezone.utc)
    path = tmp_path / "concurrent.sqlite3"
    store = SQLiteAtomicApprovalStore(path, timeout_seconds=20)
    records = _records(now)
    assert store.register_pair("auth-05", records, now=now)

    def attempt(_):
        independent = SQLiteAtomicApprovalStore(path, timeout_seconds=20)
        return independent.commit_pair_and_audit(
            "auth-05", records, {"event_type": "concurrent_attempt"}, now=now
        )

    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(attempt, range(12)))
    assert results.count(True) == 1
    assert results.count(False) == 11
    assert len(store.audit_events()) == 1
    assert store.verify_audit_chain() is True


def test_store_and_audit_survive_reopening(tmp_path):
    now = datetime.now(timezone.utc)
    path = tmp_path / "persistent.sqlite3"
    records = _records(now)
    first = SQLiteAtomicApprovalStore(path)
    assert first.register_pair("auth-06", records, now=now)
    assert first.commit_pair_and_audit(
        "auth-06", records, {"event_type": "persisted"}, now=now
    )
    reopened = SQLiteAtomicApprovalStore(path)
    assert reopened.verify_audit_chain() is True
    assert len(reopened.audit_events()) == 1
    assert reopened.commit_pair_and_audit(
        "auth-06", records, {"event_type": "replay"}, now=now
    ) is False


def test_audit_rows_reject_update_and_delete(tmp_path):
    now = datetime.now(timezone.utc)
    path = tmp_path / "append-only.sqlite3"
    store = SQLiteAtomicApprovalStore(path)
    records = _records(now)
    assert store.register_pair("auth-07", records, now=now)
    assert store.commit_pair_and_audit(
        "auth-07", records, {"event_type": "append_only"}, now=now
    )
    with sqlite3.connect(path) as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("UPDATE dual_approval_audit SET event_json='{}'")
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("DELETE FROM dual_approval_audit")


def test_hash_chain_detects_direct_database_tampering(tmp_path):
    now = datetime.now(timezone.utc)
    path = tmp_path / "tamper.sqlite3"
    store = SQLiteAtomicApprovalStore(path)
    records = _records(now)
    assert store.register_pair("auth-08", records, now=now)
    assert store.commit_pair_and_audit(
        "auth-08", records, {"event_type": "original"}, now=now
    )
    with sqlite3.connect(path) as connection:
        connection.execute("DROP TRIGGER dual_approval_audit_no_update")
        connection.execute(
            "UPDATE dual_approval_audit SET event_json='{}' WHERE sequence=1"
        )
    assert store.verify_audit_chain() is False


def test_dual_approval_engine_uses_atomic_store_callback(tmp_path):
    now = datetime.now(timezone.utc)
    expiry = now + timedelta(minutes=10)
    request = {
        "authorization_id": "auth-engine-01",
        "request_version": "v1",
        "requester_id": "requester",
        "operator_id": "operator",
        "reviewer_id": "reviewer",
        "policy_version": "policy-v1",
        "expires_at": expiry.isoformat(),
        "environment_digest": "a" * 64,
        "constraints_digest": "b" * 64,
        "action_digest": "c" * 64,
    }
    approvals = []
    records = []
    for index, subject in enumerate(("approver-a", "approver-b")):
        nonce = (str(index + 1) * 48)
        approval_expiry = now + timedelta(minutes=5)
        approvals.append({
            "subject_id": subject,
            "role": "security-approver",
            "key_id": f"key-{index}",
            "algorithm": "Ed25519",
            "approval_policy_id": "dual-v1",
            "policy_version": "policy-v1",
            "nonce": nonce,
            "issued_at": (now - timedelta(seconds=1)).isoformat(),
            "expires_at": approval_expiry.isoformat(),
            "signature": "test-signature",
        })
        records.append((nonce, approval_expiry.isoformat()))

    store = _store(tmp_path, "engine.sqlite3")
    assert store.register_pair(request["authorization_id"], tuple(records), now=now)
    result = validate_dual_approval(
        request,
        approvals,
        signature_verifier=lambda envelope, approval: True,
        identity_verifier=lambda subject, role, context: True,
        atomic_pair_audit_commit=store.atomic_commit_callback,
        now=now,
    )
    assert result["nonce_pair_and_audit_committed_atomically"] is True
    assert result["execution_authorized"] is False
    assert result["workload_executed"] is False
    assert len(store.audit_events()) == 1


def test_missing_atomic_or_legacy_commit_callbacks_fail_closed():
    now = datetime.now(timezone.utc)
    request = {
        "authorization_id": "auth-no-callback",
        "request_version": "v1",
        "requester_id": "requester",
        "operator_id": "operator",
        "reviewer_id": "reviewer",
        "policy_version": "policy-v1",
        "expires_at": (now + timedelta(minutes=5)).isoformat(),
        "environment_digest": "a" * 64,
        "constraints_digest": "b" * 64,
        "action_digest": "c" * 64,
    }
    approvals = []
    for index, subject in enumerate(("approver-a", "approver-b")):
        approvals.append({
            "subject_id": subject, "role": "security-approver",
            "key_id": f"key-{index}", "algorithm": "Ed25519",
            "approval_policy_id": "dual-v1", "policy_version": "policy-v1",
            "nonce": str(index + 1) * 48,
            "issued_at": (now - timedelta(seconds=1)).isoformat(),
            "expires_at": (now + timedelta(minutes=2)).isoformat(),
            "signature": "test-signature",
        })
    with pytest.raises(
        DualApprovalError,
        match="Separate nonce and audit callbacks are prohibited",
    ):
        validate_dual_approval(
            request, approvals,
            signature_verifier=lambda envelope, approval: True,
            identity_verifier=lambda subject, role, context: True,
            # Legacy split callbacks are deliberately insufficient: they
            # cannot prove nonce consumption and audit append are atomic.
            nonce_pair_consumer=lambda auth_id, records: True,
            audit_append=lambda event: True,
            now=now,
        )


def test_outbox_checkpoint_is_committed_with_nonce_pair_and_audit(tmp_path):
    now = datetime.now(timezone.utc)
    store = _store(tmp_path, "outbox.sqlite3")
    records = _records(now)
    assert store.register_pair("auth-outbox-01", records, now=now)

    checkpoint = store.commit_pair_audit_and_outbox(
        "auth-outbox-01", records,
        {"event_type": "dual_approval_verified", "authorization_id": "auth-outbox-01"},
        now=now,
    )
    assert checkpoint is not None
    assert checkpoint.authorization_id == "auth-outbox-01"
    assert checkpoint.sequence == 1
    assert store.anchor_outbox_status("auth-outbox-01") == "pending"
    assert store.pending_anchor_checkpoints() == [checkpoint]
    assert len(store.audit_events()) == 1
    assert store.verify_audit_chain() is True


def test_outbox_exact_retry_reuses_checkpoint_without_reconsuming_nonces(tmp_path):
    now = datetime.now(timezone.utc)
    store = _store(tmp_path, "outbox-retry.sqlite3")
    records = _records(now)
    assert store.register_pair("auth-outbox-02", records, now=now)
    event = {"event_type": "approved", "authorization_id": "auth-outbox-02"}

    first = store.commit_pair_audit_and_outbox("auth-outbox-02", records, event, now=now)
    second = store.commit_pair_audit_and_outbox("auth-outbox-02", records, event, now=now)
    assert first is not None
    assert second == first
    assert len(store.audit_events()) == 1
    assert store.pending_anchor_checkpoints() == [first]

    # Same authorization cannot be rebound to another event or nonce pair.
    assert store.commit_pair_audit_and_outbox(
        "auth-outbox-02", records, {"event_type": "different"}, now=now
    ) is None
    changed_records = (("c" * 48, records[0][1]), records[1])
    assert store.commit_pair_audit_and_outbox(
        "auth-outbox-02", changed_records, event, now=now
    ) is None
    altered_expiry = (records[0][0], (now + timedelta(minutes=20)).isoformat())
    assert store.commit_pair_audit_and_outbox(
        "auth-outbox-02", (altered_expiry, records[1]), event, now=now
    ) is None
    assert len(store.audit_events()) == 1


def test_outbox_insert_failure_rolls_back_nonces_and_audit(tmp_path):
    now = datetime.now(timezone.utc)
    path = tmp_path / "outbox-rollback.sqlite3"
    store = SQLiteAtomicApprovalStore(path)
    records = _records(now)
    assert store.register_pair("auth-outbox-03", records, now=now)
    with sqlite3.connect(path) as connection:
        connection.execute("""
            CREATE TRIGGER reject_outbox_insert
            BEFORE INSERT ON dual_approval_anchor_outbox
            BEGIN
                SELECT RAISE(ABORT, 'injected outbox failure');
            END
        """)
    assert store.commit_pair_audit_and_outbox(
        "auth-outbox-03", records, {"event_type": "must_rollback"}, now=now
    ) is None
    assert store.audit_events() == []
    assert store.pending_anchor_checkpoints() == []
    with sqlite3.connect(path) as connection:
        connection.execute("DROP TRIGGER reject_outbox_insert")
    checkpoint = store.commit_pair_audit_and_outbox(
        "auth-outbox-03", records, {"event_type": "retry_after_outbox_recovery", "authorization_id": "auth-outbox-03"}, now=now
    )
    assert checkpoint is not None
    assert len(store.audit_events()) == 1


def test_outbox_receipt_transition_is_one_way_and_idempotent(tmp_path):
    now = datetime.now(timezone.utc)
    store = _store(tmp_path, "outbox-receipt.sqlite3")
    records = _records(now)
    assert store.register_pair("auth-outbox-04", records, now=now)
    checkpoint = store.commit_pair_audit_and_outbox(
        "auth-outbox-04", records, {"event_type": "approved", "authorization_id": "auth-outbox-04"}, now=now
    )
    receipt = {"receipt_id": "external-123"}
    assert checkpoint is not None
    assert store.mark_checkpoint_anchored(
        checkpoint.authorization_id, checkpoint.event_hash, receipt
    ) is True
    assert store.anchor_outbox_status("auth-outbox-04") == "anchored"
    assert store.pending_anchor_checkpoints() == []
    assert store.mark_checkpoint_anchored(
        checkpoint.authorization_id, checkpoint.event_hash, receipt
    ) is True
    assert store.mark_checkpoint_anchored(
        checkpoint.authorization_id, checkpoint.event_hash, {"receipt_id": "different"}
    ) is False


def test_outbox_integrity_verifier_accepts_pending_and_anchored_rows(tmp_path):
    now = datetime.now(timezone.utc)
    store = _store(tmp_path, "outbox-integrity.sqlite3")
    records = _records(now)
    assert store.register_pair("auth-integrity-01", records, now=now)
    checkpoint = store.commit_pair_audit_and_outbox(
        "auth-integrity-01", records,
        {"event_type": "verified", "authorization_id": "auth-integrity-01"},
        now=now,
    )
    assert checkpoint is not None
    assert store.verify_anchor_outbox() is True
    assert store.mark_checkpoint_anchored(
        checkpoint.authorization_id, checkpoint.event_hash,
        {"receipt_id": "receipt-1"},
    ) is True
    assert store.verify_anchor_outbox() is True


def test_outbox_integrity_verifier_detects_database_tampering(tmp_path):
    now = datetime.now(timezone.utc)
    path = tmp_path / "outbox-tamper.sqlite3"
    store = SQLiteAtomicApprovalStore(path)
    records = _records(now)
    assert store.register_pair("auth-integrity-02", records, now=now)
    checkpoint = store.commit_pair_audit_and_outbox(
        "auth-integrity-02", records, {"event_type": "verified", "authorization_id": "auth-integrity-02"}, now=now
    )
    assert checkpoint is not None
    assert store.verify_anchor_outbox() is True
    with sqlite3.connect(path) as connection:
        connection.execute("DROP TRIGGER anchor_outbox_immutable_fields")
        connection.execute(
            "UPDATE dual_approval_anchor_outbox SET event_json='{}' WHERE authorization_id=?",
            ("auth-integrity-02",),
        )
    assert store.verify_anchor_outbox() is False


def test_concurrent_outbox_commit_has_one_checkpoint_and_one_audit(tmp_path):
    now = datetime.now(timezone.utc)
    path = tmp_path / "outbox-concurrent.sqlite3"
    records = _records(now)
    store = SQLiteAtomicApprovalStore(path, timeout_seconds=20)
    assert store.register_pair("auth-outbox-concurrent", records, now=now)
    event = {"event_type": "concurrent", "authorization_id": "auth-outbox-concurrent"}

    def attempt(_):
        independent = SQLiteAtomicApprovalStore(path, timeout_seconds=20)
        return independent.commit_pair_audit_and_outbox(
            "auth-outbox-concurrent", records, event, now=now
        )

    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(attempt, range(12)))
    checkpoints = [item for item in results if item is not None]
    assert len(checkpoints) == 12
    assert all(item == checkpoints[0] for item in checkpoints)
    assert len(store.audit_events()) == 1
    assert store.pending_anchor_checkpoints() == [checkpoints[0]]
    assert store.verify_audit_chain() is True
    assert store.verify_anchor_outbox() is True


def test_multiprocess_outbox_retry_returns_one_durable_checkpoint(tmp_path):
    """Independent OS processes must converge on one idempotent outbox row.

    This exercises SQLite process-level locking on one local host. It does not
    establish safety for multiple hosts or network filesystems.
    """
    now = datetime.now(timezone.utc)
    path = tmp_path / "outbox-multiprocess.sqlite3"
    store = SQLiteAtomicApprovalStore(path, timeout_seconds=30)
    records = _records(now)
    authorization_id = "auth-outbox-multiprocess"
    event = {
        "event_type": "multiprocess-concurrent",
        "authorization_id": authorization_id,
    }
    assert store.register_pair(authorization_id, records, now=now)

    args = (store, authorization_id, records, event, now)
    with ProcessPoolExecutor(
        max_workers=8,
        mp_context=multiprocessing.get_context("spawn"),
    ) as pool:
        results = list(pool.map(_process_outbox_commit, [args] * 8))

    checkpoints = [item for item in results if item is not None]
    assert len(checkpoints) == 8
    assert all(item == checkpoints[0] for item in checkpoints)
    assert len(store.audit_events()) == 1
    assert store.pending_anchor_checkpoints() == [checkpoints[0]]
    assert store.verify_audit_chain() is True
    assert store.verify_anchor_outbox() is True


def test_crash_after_durable_commit_retries_original_checkpoint(tmp_path):
    """A lost caller acknowledgement must not duplicate a committed approval."""
    now = datetime.now(timezone.utc)
    path = tmp_path / "outbox-crash-after-commit.sqlite3"
    store = SQLiteAtomicApprovalStore(path, timeout_seconds=30)
    records = _records(now)
    authorization_id = "auth-crash-after-commit"
    event = {
        "event_type": "crash-after-commit",
        "authorization_id": authorization_id,
    }
    assert store.register_pair(authorization_id, records, now=now)

    args = (store, authorization_id, records, event, now)
    process = multiprocessing.get_context("spawn").Process(
        target=_process_commit_then_exit_without_ack,
        args=(args,),
    )
    process.start()
    process.join(timeout=30)
    if process.is_alive():
        process.terminate()
        process.join()
        pytest.fail("crash simulation process did not terminate")
    assert process.exitcode == 23

    # Reopen from disk as a fresh process would, then replay the exact request.
    reopened = SQLiteAtomicApprovalStore(path, timeout_seconds=30)
    recovered = reopened.commit_pair_audit_and_outbox(
        authorization_id, records, event, now=now
    )
    assert recovered is not None
    assert reopened.commit_pair_audit_and_outbox(
        authorization_id, records, event, now=now
    ) == recovered
    assert len(reopened.audit_events()) == 1
    assert reopened.pending_anchor_checkpoints() == [recovered]
    assert reopened.verify_audit_chain() is True
    assert reopened.verify_anchor_outbox() is True


def test_crash_before_sqlite_commit_rolls_back_and_allows_clean_retry(tmp_path):
    """A process death before COMMIT must leave no partial nonce/audit/outbox state."""
    now = datetime.now(timezone.utc)
    path = tmp_path / "outbox-crash-before-commit.sqlite3"
    store = SQLiteAtomicApprovalStore(path, timeout_seconds=30)
    records = _records(now)
    authorization_id = "auth-crash-before-commit"
    event = {
        "event_type": "crash-before-commit",
        "authorization_id": authorization_id,
    }
    assert store.register_pair(authorization_id, records, now=now)

    args = (str(path), authorization_id, records, event, now)
    process = multiprocessing.get_context("spawn").Process(
        target=_process_exit_before_sqlite_commit,
        args=(args,),
    )
    process.start()
    process.join(timeout=30)
    if process.is_alive():
        process.terminate()
        process.join()
        pytest.fail("pre-commit crash simulation process did not terminate")
    assert process.exitcode == 25

    # SQLite must roll back the uncommitted transaction when the process dies.
    reopened = SQLiteAtomicApprovalStore(path, timeout_seconds=30)
    assert reopened.audit_events() == []
    assert reopened.pending_anchor_checkpoints() == []
    assert reopened.verify_audit_chain() is True
    assert reopened.verify_anchor_outbox() is True

    # The original nonce pair must still be usable after the rollback.
    checkpoint = reopened.commit_pair_audit_and_outbox(
        authorization_id, records, event, now=now
    )
    assert checkpoint is not None
    assert len(reopened.audit_events()) == 1
    assert reopened.pending_anchor_checkpoints() == [checkpoint]
    assert reopened.verify_audit_chain() is True
    assert reopened.verify_anchor_outbox() is True


def test_dual_approval_engine_can_use_only_verified_external_anchor_callback(tmp_path):
    from final_tec_audit_anchor import ExternalAuditAnchorCoordinator

    class TestAnchor:
        def append_checkpoint(self, sequence, previous_hash, event_hash, created_at_utc):
            return {"receipt_id": f"checkpoint-{sequence}", "event_hash": event_hash}

        def verify_checkpoint(self, sequence, previous_hash, event_hash, created_at_utc, receipt):
            return receipt == {
                "receipt_id": f"checkpoint-{sequence}",
                "event_hash": event_hash,
            }

    now = datetime.now(timezone.utc)
    expiry = now + timedelta(minutes=10)
    request = {
        "authorization_id": "auth-engine-external-01",
        "request_version": "v1",
        "requester_id": "requester",
        "operator_id": "operator",
        "reviewer_id": "reviewer",
        "policy_version": "policy-v1",
        "expires_at": expiry.isoformat(),
        "environment_digest": "a" * 64,
        "constraints_digest": "b" * 64,
        "action_digest": "c" * 64,
    }
    approvals = []
    records = []
    for index, subject in enumerate(("approver-a", "approver-b")):
        nonce = (str(index + 3) * 48)
        approval_expiry = now + timedelta(minutes=5)
        approvals.append({
            "subject_id": subject,
            "role": "security-approver",
            "key_id": f"external-key-{index}",
            "algorithm": "Ed25519",
            "approval_policy_id": "dual-v1",
            "policy_version": "policy-v1",
            "nonce": nonce,
            "issued_at": (now - timedelta(seconds=1)).isoformat(),
            "expires_at": approval_expiry.isoformat(),
            "signature": "test-signature",
        })
        records.append((nonce, approval_expiry.isoformat()))

    store = _store(tmp_path, "engine-external-anchor.sqlite3")
    assert store.register_pair(request["authorization_id"], tuple(records), now=now)
    coordinator = ExternalAuditAnchorCoordinator(store, TestAnchor())
    result = validate_dual_approval(
        request,
        approvals,
        signature_verifier=lambda envelope, approval: True,
        identity_verifier=lambda subject, role, context: True,
        atomic_pair_audit_commit=coordinator.callback(),
        now=now,
    )
    assert result["nonce_pair_and_audit_committed_atomically"] is True
    assert result["execution_authorized"] is False
    assert store.anchor_outbox_status(request["authorization_id"]) == "anchored"
    assert store.pending_anchor_checkpoints() == []
    assert store.verify_audit_chain() is True
    assert store.verify_anchor_outbox() is True



def test_anchor_recovery_handles_lost_append_response_idempotently(tmp_path):
    """A remote append committed before response loss must be safe to retry."""
    from final_tec_audit_anchor import ExternalAuditAnchorCoordinator

    class LostFirstResponseAnchor:
        def __init__(self):
            self.receipts = {}
            self.append_calls = 0

        def append_checkpoint(self, sequence, previous_hash, event_hash, created_at_utc):
            key = (sequence, previous_hash, event_hash, created_at_utc)
            self.append_calls += 1
            receipt = self.receipts.setdefault(
                key, {"receipt_id": f"remote-{sequence}", "event_hash": event_hash}
            )
            if self.append_calls == 1:
                # Model remote durability followed by a lost network response.
                raise TimeoutError("response lost after remote append")
            return receipt

        def verify_checkpoint(self, sequence, previous_hash, event_hash, created_at_utc, receipt):
            key = (sequence, previous_hash, event_hash, created_at_utc)
            return self.receipts.get(key) == receipt

    now = datetime.now(timezone.utc)
    store = _store(tmp_path, "outbox-lost-anchor-response.sqlite3")
    records = _records(now)
    authorization_id = "auth-anchor-lost-response"
    event = {
        "event_type": "anchor-recovery",
        "authorization_id": authorization_id,
    }
    assert store.register_pair(authorization_id, records, now=now)
    anchor = LostFirstResponseAnchor()
    coordinator = ExternalAuditAnchorCoordinator(store, anchor)

    # The ledger commit is durable even though the remote acknowledgement is lost.
    assert coordinator.commit_and_anchor(authorization_id, records, event) is False
    pending = store.pending_anchor_checkpoints()
    assert len(pending) == 1
    assert store.anchor_outbox_status(authorization_id) == "pending"
    assert len(store.audit_events()) == 1

    # Recovery replays the identical checkpoint; the remote anchor returns its
    # original receipt rather than appending a duplicate.
    assert coordinator.recover_pending() == 1
    assert anchor.append_calls == 2
    assert len(anchor.receipts) == 1
    assert store.pending_anchor_checkpoints() == []
    assert store.anchor_outbox_status(authorization_id) == "anchored"
    assert len(store.audit_events()) == 1
    assert store.verify_audit_chain() is True
    assert store.verify_anchor_outbox() is True


def test_anchor_recovery_retries_when_local_receipt_mark_fails(tmp_path):
    """A verified remote receipt must remain recoverable if local marking fails."""
    from final_tec_audit_anchor import ExternalAuditAnchorCoordinator

    class FailFirstLocalMarkStore(SQLiteAtomicApprovalStore):
        def __init__(self, path):
            super().__init__(path, timeout_seconds=30)
            self.mark_calls = 0

        def mark_checkpoint_anchored(self, authorization_id, event_hash, receipt):
            self.mark_calls += 1
            if self.mark_calls == 1:
                return False
            return super().mark_checkpoint_anchored(
                authorization_id, event_hash, receipt
            )

    class IdempotentAnchor:
        def __init__(self):
            self.receipts = {}
            self.append_calls = 0

        def append_checkpoint(self, sequence, previous_hash, event_hash, created_at_utc):
            self.append_calls += 1
            key = (sequence, previous_hash, event_hash, created_at_utc)
            return self.receipts.setdefault(
                key, {"receipt_id": f"durable-{sequence}", "event_hash": event_hash}
            )

        def verify_checkpoint(self, sequence, previous_hash, event_hash, created_at_utc, receipt):
            key = (sequence, previous_hash, event_hash, created_at_utc)
            return self.receipts.get(key) == receipt

    now = datetime.now(timezone.utc)
    path = tmp_path / "outbox-local-mark-failure.sqlite3"
    store = FailFirstLocalMarkStore(path)
    records = _records(now)
    authorization_id = "auth-anchor-local-mark-failure"
    event = {
        "event_type": "anchor-local-mark-recovery",
        "authorization_id": authorization_id,
    }
    assert store.register_pair(authorization_id, records, now=now)
    anchor = IdempotentAnchor()
    coordinator = ExternalAuditAnchorCoordinator(store, anchor)

    # Remote receipt is durable and verified, but local status update fails.
    assert coordinator.commit_and_anchor(authorization_id, records, event) is False
    assert anchor.append_calls == 1
    assert store.anchor_outbox_status(authorization_id) == "pending"
    assert len(store.pending_anchor_checkpoints()) == 1

    # Recovery repeats the idempotent append and completes the local transition.
    assert coordinator.recover_pending() == 1
    assert anchor.append_calls == 2
    assert len(anchor.receipts) == 1
    assert store.mark_calls == 2
    assert store.anchor_outbox_status(authorization_id) == "anchored"
    assert store.pending_anchor_checkpoints() == []
    assert len(store.audit_events()) == 1
    assert store.verify_audit_chain() is True
    assert store.verify_anchor_outbox() is True


def test_anchor_recovery_continues_after_one_checkpoint_temporarily_fails(tmp_path):
    """One unavailable checkpoint must not block recovery of later outbox rows."""
    from final_tec_audit_anchor import ExternalAuditAnchorCoordinator

    class OneCheckpointTemporarilyUnavailable:
        def __init__(self, failing_event_hash):
            self.failing_event_hash = failing_event_hash
            self.failed_once = False
            self.receipts = {}
            self.attempts = []

        def append_checkpoint(self, sequence, previous_hash, event_hash, created_at_utc):
            self.attempts.append(event_hash)
            if event_hash == self.failing_event_hash and not self.failed_once:
                self.failed_once = True
                raise TimeoutError("temporary anchor outage for this checkpoint")
            key = (sequence, previous_hash, event_hash, created_at_utc)
            return self.receipts.setdefault(
                key, {"receipt_id": f"recovery-{sequence}", "event_hash": event_hash}
            )

        def verify_checkpoint(self, sequence, previous_hash, event_hash, created_at_utc, receipt):
            key = (sequence, previous_hash, event_hash, created_at_utc)
            return self.receipts.get(key) == receipt

    now = datetime.now(timezone.utc)
    store = _store(tmp_path, "outbox-independent-recovery.sqlite3")
    first_id = "auth-independent-recovery-1"
    second_id = "auth-independent-recovery-2"
    first_records = _records(now)
    second_records = (("c" * 48, first_records[0][1]), ("d" * 48, first_records[1][1]))
    first_event = {"event_type": "pending-one", "authorization_id": first_id}
    second_event = {"event_type": "pending-two", "authorization_id": second_id}

    assert store.register_pair(first_id, first_records, now=now)
    assert store.register_pair(second_id, second_records, now=now)
    first_checkpoint = store.commit_pair_audit_and_outbox(
        first_id, first_records, first_event, now=now
    )
    second_checkpoint = store.commit_pair_audit_and_outbox(
        second_id, second_records, second_event, now=now
    )
    assert first_checkpoint is not None
    assert second_checkpoint is not None

    anchor = OneCheckpointTemporarilyUnavailable(first_checkpoint.event_hash)
    coordinator = ExternalAuditAnchorCoordinator(store, anchor)

    # The first item fails, but recovery continues and anchors the second item.
    assert coordinator.recover_pending() == 1
    assert store.anchor_outbox_status(first_id) == "pending"
    assert store.anchor_outbox_status(second_id) == "anchored"
    assert store.pending_anchor_checkpoints() == [first_checkpoint]
    assert any(key[2] == second_checkpoint.event_hash for key in anchor.receipts)

    # A later pass recovers the remaining checkpoint without duplicating the
    # already anchored second checkpoint.
    attempts_before_retry = len(anchor.attempts)
    assert coordinator.recover_pending() == 1
    assert len(anchor.attempts) == attempts_before_retry + 1
    assert store.anchor_outbox_status(first_id) == "anchored"
    assert store.anchor_outbox_status(second_id) == "anchored"
    assert store.pending_anchor_checkpoints() == []
    assert len(store.audit_events()) == 2
    assert store.verify_audit_chain() is True
    assert store.verify_anchor_outbox() is True


def test_anchor_recovery_retries_after_sqlite_receipt_update_aborts(tmp_path):
    """A real SQLite update failure must leave the outbox pending for retry."""
    from final_tec_audit_anchor import ExternalAuditAnchorCoordinator

    class IdempotentAnchor:
        def __init__(self):
            self.receipts = {}
            self.append_calls = 0

        def append_checkpoint(self, sequence, previous_hash, event_hash, created_at_utc):
            self.append_calls += 1
            key = (sequence, previous_hash, event_hash, created_at_utc)
            return self.receipts.setdefault(
                key, {"receipt_id": f"sqlite-retry-{sequence}", "event_hash": event_hash}
            )

        def verify_checkpoint(self, sequence, previous_hash, event_hash, created_at_utc, receipt):
            key = (sequence, previous_hash, event_hash, created_at_utc)
            return self.receipts.get(key) == receipt

    now = datetime.now(timezone.utc)
    store = _store(tmp_path, "outbox-sqlite-receipt-update-abort.sqlite3")
    records = _records(now)
    authorization_id = "auth-sqlite-receipt-update-abort"
    event = {"event_type": "sqlite-update-abort", "authorization_id": authorization_id}
    assert store.register_pair(authorization_id, records, now=now)
    checkpoint = store.commit_pair_audit_and_outbox(
        authorization_id, records, event, now=now
    )
    assert checkpoint is not None

    connection = store._connect()
    try:
        connection.execute(
            """CREATE TRIGGER reject_anchor_receipt_update
               BEFORE UPDATE ON dual_approval_anchor_outbox
               WHEN NEW.status = 'anchored'
               BEGIN
                   SELECT RAISE(ABORT, 'simulated durable receipt update failure');
               END"""
        )
        connection.commit()
    finally:
        connection.close()

    anchor = IdempotentAnchor()
    coordinator = ExternalAuditAnchorCoordinator(store, anchor)

    # The external receipt exists, but SQLite rejects the local state transition.
    assert coordinator.recover_pending() == 0
    assert store.anchor_outbox_status(authorization_id) == "pending"
    assert anchor.append_calls == 1
    assert store.verify_audit_chain() is True
    assert store.verify_anchor_outbox() is True

    connection = store._connect()
    try:
        connection.execute("DROP TRIGGER reject_anchor_receipt_update")
        connection.commit()
    finally:
        connection.close()

    # Recovery reuses the same idempotent receipt and completes the local update.
    assert coordinator.recover_pending() == 1
    assert anchor.append_calls == 2
    assert store.anchor_outbox_status(authorization_id) == "anchored"
    assert store.pending_anchor_checkpoints() == []
    assert store.verify_audit_chain() is True
    assert store.verify_anchor_outbox() is True


def test_anchor_recovery_skips_invalid_checkpoint_and_continues(tmp_path):
    """Malformed pending data must fail closed without blocking valid entries."""
    from dataclasses import replace
    from final_tec_audit_anchor import ExternalAuditAnchorCoordinator

    class LedgerWithMalformedPendingEntry:
        def __init__(self, ledger, malformed, valid):
            self.ledger = ledger
            self.malformed = malformed
            self.valid = valid

        def pending_anchor_checkpoints(self):
            return [self.malformed, self.valid]

        def mark_checkpoint_anchored(self, authorization_id, event_hash, receipt):
            return self.ledger.mark_checkpoint_anchored(
                authorization_id, event_hash, receipt
            )

    class RecordingAnchor:
        def __init__(self):
            self.calls = []

        def append_checkpoint(self, sequence, previous_hash, event_hash, created_at_utc):
            self.calls.append(event_hash)
            return {"receipt_id": f"valid-{sequence}", "event_hash": event_hash}

        def verify_checkpoint(self, sequence, previous_hash, event_hash, created_at_utc, receipt):
            return receipt == {
                "receipt_id": f"valid-{sequence}",
                "event_hash": event_hash,
            }

    now = datetime.now(timezone.utc)
    store = _store(tmp_path, "outbox-invalid-pending-entry.sqlite3")
    records = _records(now)
    authorization_id = "auth-invalid-pending-entry"
    event = {"event_type": "valid-pending", "authorization_id": authorization_id}
    assert store.register_pair(authorization_id, records, now=now)
    checkpoint = store.commit_pair_audit_and_outbox(
        authorization_id, records, event, now=now
    )
    assert checkpoint is not None

    malformed = replace(checkpoint, sequence=0)
    ledger = LedgerWithMalformedPendingEntry(store, malformed, checkpoint)
    anchor = RecordingAnchor()
    coordinator = ExternalAuditAnchorCoordinator(ledger, anchor)

    assert coordinator.recover_pending() == 1
    assert anchor.calls == [checkpoint.event_hash]
    assert store.anchor_outbox_status(authorization_id) == "anchored"
    assert store.pending_anchor_checkpoints() == []
    assert store.verify_audit_chain() is True
    assert store.verify_anchor_outbox() is True


def test_outbox_rejects_audit_event_with_missing_or_mismatched_authorization_id(tmp_path):
    now = datetime.now(timezone.utc)
    store = _store(tmp_path, "outbox-authorization-binding.sqlite3")
    records = _records(now)
    assert store.register_pair("auth-bound-01", records, now=now)

    assert store.commit_pair_audit_and_outbox(
        "auth-bound-01", records, {"event_type": "missing-id"}, now=now
    ) is None
    assert store.commit_pair_audit_and_outbox(
        "auth-bound-01", records,
        {"event_type": "wrong-id", "authorization_id": "another-authorization"},
        now=now,
    ) is None
    assert store.audit_events() == []
    assert store.pending_anchor_checkpoints() == []

    # Rejection must leave both registered nonces available for the correctly
    # bound event, proving the check happens before any transactional consume.
    checkpoint = store.commit_pair_audit_and_outbox(
        "auth-bound-01", records,
        {"event_type": "correct", "authorization_id": "auth-bound-01"},
        now=now,
    )
    assert checkpoint is not None
    assert len(store.audit_events()) == 1

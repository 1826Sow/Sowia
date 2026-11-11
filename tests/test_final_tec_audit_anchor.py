from datetime import datetime, timezone

from final_tec_audit_anchor import (
    AuditCheckpoint,
    ExternalAuditAnchorCoordinator,
)


class FakeOutboxLedger:
    def __init__(self):
        self.checkpoint = None
        self.commit_calls = 0
        self.anchored = False
        self.receipt = None

    def commit_pair_audit_and_outbox(self, authorization_id, nonce_records, audit_event):
        self.commit_calls += 1
        if self.checkpoint is None:
            self.checkpoint = AuditCheckpoint(
                authorization_id=authorization_id,
                sequence=7,
                previous_hash="a" * 64,
                event_hash="b" * 64,
                created_at_utc=datetime.now(timezone.utc).isoformat(),
            )
        # Idempotent retry: return the same durable outbox checkpoint.
        return self.checkpoint

    def mark_checkpoint_anchored(self, authorization_id, event_hash, receipt):
        if not self.checkpoint or authorization_id != self.checkpoint.authorization_id:
            return False
        if event_hash != self.checkpoint.event_hash:
            return False
        self.anchored = True
        self.receipt = dict(receipt)
        return True


class FakeExternalAnchor:
    def __init__(self, *, verify=True, fail_append=False):
        self.verify_result = verify
        self.fail_append = fail_append
        self.append_calls = 0
        self.verify_calls = 0
        self.receipt = {"receipt_id": "test-receipt-7"}

    def append_checkpoint(self, sequence, previous_hash, event_hash, created_at_utc):
        self.append_calls += 1
        if self.fail_append:
            raise RuntimeError("simulated provider outage")
        return dict(self.receipt)

    def verify_checkpoint(self, sequence, previous_hash, event_hash, created_at_utc, receipt):
        self.verify_calls += 1
        return self.verify_result and receipt == self.receipt


def test_success_requires_external_receipt_verification_and_durable_mark():
    ledger = FakeOutboxLedger()
    anchor = FakeExternalAnchor()
    coordinator = ExternalAuditAnchorCoordinator(ledger, anchor)

    assert coordinator.callback()("auth-1", (("n" * 48, "expiry"),), {"event": "approved"}) is True
    assert ledger.anchored is True
    assert ledger.receipt == anchor.receipt
    assert anchor.append_calls == 1
    assert anchor.verify_calls == 1


def test_provider_outage_fails_closed_and_retry_reuses_same_outbox_checkpoint():
    ledger = FakeOutboxLedger()
    anchor = FakeExternalAnchor(fail_append=True)
    coordinator = ExternalAuditAnchorCoordinator(ledger, anchor)

    args = ("auth-2", (("n" * 48, "expiry"),), {"event": "approved"})
    assert coordinator.commit_and_anchor(*args) is False
    assert ledger.anchored is False
    first_checkpoint = ledger.checkpoint

    anchor.fail_append = False
    assert coordinator.commit_and_anchor(*args) is True
    assert ledger.checkpoint == first_checkpoint
    assert ledger.commit_calls == 2
    assert ledger.anchored is True


def test_invalid_external_receipt_or_failed_verification_never_marks_anchored():
    for anchor in (FakeExternalAnchor(verify=False),):
        ledger = FakeOutboxLedger()
        coordinator = ExternalAuditAnchorCoordinator(ledger, anchor)
        assert coordinator.commit_and_anchor(
            "auth-3", (("n" * 48, "expiry"),), {"event": "approved"}
        ) is False
        assert ledger.anchored is False


def test_wrong_authorization_checkpoint_is_rejected_before_provider_call():
    ledger = FakeOutboxLedger()
    ledger.checkpoint = AuditCheckpoint(
        authorization_id="other-auth",
        sequence=1,
        previous_hash="a" * 64,
        event_hash="b" * 64,
        created_at_utc=datetime.now(timezone.utc).isoformat(),
    )
    anchor = FakeExternalAnchor()
    coordinator = ExternalAuditAnchorCoordinator(ledger, anchor)
    assert coordinator.commit_and_anchor(
        "auth-4", (("n" * 48, "expiry"),), {"event": "approved"}
    ) is False
    assert anchor.append_calls == 0


def test_real_sqlite_outbox_retries_external_anchor_without_nonce_replay(tmp_path):
    from datetime import timedelta
    from final_tec_atomic_approval_store import SQLiteAtomicApprovalStore

    now = datetime.now(timezone.utc)
    expiry = (now + timedelta(minutes=10)).isoformat()
    records = (("x" * 48, expiry), ("y" * 48, expiry))
    ledger = SQLiteAtomicApprovalStore(tmp_path / "coordinator-outbox.sqlite3")
    assert ledger.register_pair("auth-real-outbox", records, now=now)

    anchor = FakeExternalAnchor(fail_append=True)
    coordinator = ExternalAuditAnchorCoordinator(ledger, anchor)
    event = {"event_type": "dual_approval_verified", "authorization_id": "auth-real-outbox"}

    assert coordinator.commit_and_anchor("auth-real-outbox", records, event) is False
    pending = ledger.pending_anchor_checkpoints()
    assert len(pending) == 1
    assert ledger.anchor_outbox_status("auth-real-outbox") == "pending"
    assert len(ledger.audit_events()) == 1

    # Simulate process restart and provider recovery. Recovery reads only
    # the durable outbox; it does not need nonce values or re-run validation.
    anchor.fail_append = False
    restarted_coordinator = ExternalAuditAnchorCoordinator(ledger, anchor)
    assert restarted_coordinator.recover_pending() == 1
    assert ledger.anchor_outbox_status("auth-real-outbox") == "anchored"
    assert ledger.pending_anchor_checkpoints() == []
    assert len(ledger.audit_events()) == 1
    assert ledger.verify_audit_chain() is True



def test_recovery_stays_fail_closed_when_provider_is_still_unavailable(tmp_path):
    from datetime import timedelta
    from final_tec_atomic_approval_store import SQLiteAtomicApprovalStore

    now = datetime.now(timezone.utc)
    records = (("m" * 48, (now + timedelta(minutes=10)).isoformat()),
               ("n" * 48, (now + timedelta(minutes=10)).isoformat()))
    ledger = SQLiteAtomicApprovalStore(tmp_path / "pending-recovery.sqlite3")
    assert ledger.register_pair("auth-pending-recovery", records, now=now)
    anchor = FakeExternalAnchor(fail_append=True)
    coordinator = ExternalAuditAnchorCoordinator(ledger, anchor)
    assert coordinator.commit_and_anchor(
        "auth-pending-recovery", records, {"event_type": "pending", "authorization_id": "auth-pending-recovery"}
    ) is False
    assert coordinator.recover_pending() == 0
    assert ledger.anchor_outbox_status("auth-pending-recovery") == "pending"
    assert len(ledger.audit_events()) == 1


def test_pending_outbox_survives_sqlite_reopen_and_recovers_without_nonce_replay(tmp_path):
    from datetime import timedelta
    from final_tec_atomic_approval_store import SQLiteAtomicApprovalStore

    path = tmp_path / "durable-process-restart.sqlite3"
    now = datetime.now(timezone.utc)
    records = (
        ("p" * 48, (now + timedelta(minutes=10)).isoformat()),
        ("q" * 48, (now + timedelta(minutes=10)).isoformat()),
    )
    first_store = SQLiteAtomicApprovalStore(path)
    assert first_store.register_pair("auth-reopen-01", records, now=now)

    unavailable_anchor = FakeExternalAnchor(fail_append=True)
    first_coordinator = ExternalAuditAnchorCoordinator(first_store, unavailable_anchor)
    event = {"event_type": "dual_approval_verified", "authorization_id": "auth-reopen-01"}

    # The first process commits nonce consumption + audit + pending outbox,
    # then fails to reach the external anchor.
    assert first_coordinator.commit_and_anchor("auth-reopen-01", records, event) is False
    assert first_store.anchor_outbox_status("auth-reopen-01") == "pending"
    assert len(first_store.audit_events()) == 1

    # Drop every Python object associated with the first process and reopen
    # the same durable SQLite file as a new process would.
    del first_coordinator
    del first_store
    reopened_store = SQLiteAtomicApprovalStore(path)
    assert reopened_store.anchor_outbox_status("auth-reopen-01") == "pending"
    pending = reopened_store.pending_anchor_checkpoints()
    assert len(pending) == 1

    recovered_anchor = FakeExternalAnchor()
    restarted_coordinator = ExternalAuditAnchorCoordinator(reopened_store, recovered_anchor)
    assert restarted_coordinator.recover_pending() == 1
    assert reopened_store.anchor_outbox_status("auth-reopen-01") == "anchored"
    assert reopened_store.pending_anchor_checkpoints() == []
    assert len(reopened_store.audit_events()) == 1
    assert reopened_store.verify_audit_chain() is True
    assert reopened_store.verify_anchor_outbox() is True

    # Replaying the original approval callback cannot create another audit
    # entry or consume a different pair under the same authorization.
    assert reopened_store.commit_pair_audit_and_outbox(
        "auth-reopen-01", records, event, now=now
    ) == pending[0]
    assert len(reopened_store.audit_events()) == 1
    assert recovered_anchor.append_calls == 1



def test_checkpoint_rejects_non_utc_offset_and_naive_timestamp():
    from final_tec_audit_anchor import _valid_checkpoint

    for timestamp in ("2026-11-11T12:00:00+01:00", "2026-11-11T12:00:00"):
        checkpoint = AuditCheckpoint(
            authorization_id="auth-time",
            sequence=1,
            previous_hash="a" * 64,
            event_hash="b" * 64,
            created_at_utc=timestamp,
        )
        assert _valid_checkpoint(checkpoint, "auth-time") is False


def test_checkpoint_rejects_empty_or_non_string_authorization_id():
    from final_tec_audit_anchor import _valid_checkpoint

    for authorization_id in ("", "   ", None):
        checkpoint = AuditCheckpoint(
            authorization_id=authorization_id,
            sequence=1,
            previous_hash="a" * 64,
            event_hash="b" * 64,
            created_at_utc=datetime.now(timezone.utc).isoformat(),
        )
        assert _valid_checkpoint(checkpoint, authorization_id) is False

def test_sqlite_outbox_rejects_audit_event_for_another_authorization(tmp_path):
    from datetime import timedelta
    from final_tec_atomic_approval_store import SQLiteAtomicApprovalStore

    now = datetime.now(timezone.utc)
    expiry = (now + timedelta(minutes=10)).isoformat()
    records = (("r" * 48, expiry), ("s" * 48, expiry))
    ledger = SQLiteAtomicApprovalStore(tmp_path / "mismatched-audit-auth.sqlite3")
    assert ledger.register_pair("auth-bound", records, now=now)

    # A valid pair cannot be consumed under an event naming another approval.
    checkpoint = ledger.commit_pair_audit_and_outbox(
        "auth-bound",
        records,
        {"event_type": "dual_approval_verified", "authorization_id": "auth-other"},
        now=now,
    )
    assert checkpoint is None
    assert ledger.audit_events() == []
    assert ledger.pending_anchor_checkpoints() == []
    assert ledger.verify_anchor_outbox() is True

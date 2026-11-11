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
        "auth-pending-recovery", records, {"event_type": "pending"}
    ) is False
    assert coordinator.recover_pending() == 0
    assert ledger.anchor_outbox_status("auth-pending-recovery") == "pending"
    assert len(ledger.audit_events()) == 1

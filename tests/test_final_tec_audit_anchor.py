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

import copy

import pytest

from final_tec_audit_trail import (
    AuditTrailError,
    GENESIS_HASH,
    append_audit_event,
    build_audit_summary,
    create_audit_event,
    verify_audit_chain,
)


def event(previous=GENESIS_HASH, **overrides):
    args = {
        "actor_id": "reviewer-1",
        "actor_role": "final_tec_admin",
        "action": "evidence_reviewed",
        "resource_type": "evidence",
        "resource_id": "evidence-001",
        "outcome": "accepted",
        "occurred_at": "2026-11-11T11:00:00+00:00",
        "reason_code": "review_complete",
        "previous_hash": previous,
    }
    args.update(overrides)
    return create_audit_event(**args)


def test_appends_immutable_copy_and_verifies_chain():
    first = event()
    source = []
    chain = append_audit_event(source, first)
    assert source == []
    assert chain == [first]
    second = event(previous=first["event_hash"], action="evidence_publication_requested")
    chain2 = append_audit_event(chain, second)
    assert len(chain) == 1
    assert len(chain2) == 2
    assert verify_audit_chain(chain2)


def test_detects_event_tampering_and_reordering():
    first = event()
    second = event(previous=first["event_hash"], action="evidence_rejected")
    chain = [first, second]
    altered = copy.deepcopy(chain)
    altered[0]["outcome"] = "completed"
    assert not verify_audit_chain(altered)
    assert not verify_audit_chain(list(reversed(chain)))


def test_rejects_wrong_previous_hash():
    first = event()
    with pytest.raises(AuditTrailError):
        append_audit_event([first], event())


@pytest.mark.parametrize("role", ["owner", "admin", "unknown"])
def test_rejects_unrecognized_actor_roles(role):
    with pytest.raises(AuditTrailError):
        event(actor_role=role)


def test_rejects_naive_timestamps_and_unknown_actions():
    with pytest.raises(AuditTrailError):
        event(occurred_at="2026-11-11T11:00:00")
    with pytest.raises(AuditTrailError):
        event(action="free_text_action")


def test_summary_requires_valid_chain_and_reports_no_persistence():
    first = event()
    summary = build_audit_summary([first])
    assert summary["event_count"] == 1
    assert summary["integrity"] == "valid"
    assert summary["storage_mode"] == "memory_only"
    assert "durable" in summary["notice"]
    with pytest.raises(AuditTrailError):
        build_audit_summary([{"event_hash": "bad"}])


def test_rejects_freeform_sensitive_fields_by_schema():
    with pytest.raises(TypeError):
        event(password="do-not-store")

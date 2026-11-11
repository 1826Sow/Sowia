import copy

import pytest

from final_tec_evidence_review import EvidenceReviewError, build_evidence_review_decision


def pending_record():
    return {
        "project_key": "final-tec",
        "metric_key": "edge_latency",
        "title": "Rapport de latence",
        "category": "ai_edge_tests",
        "evidence_status": "pending",
        "publication_state": "draft",
        "source_url": "https://evidence.example/report-1",
        "observed_at": "2026-11-11T09:00:00+00:00",
        "evidence_ref": "report-1",
        "evidence_owner": "submitter-1",
    }


def review(**overrides):
    args = {
        "record": pending_record(),
        "reviewer_id": "reviewer-2",
        "reviewer_role": "final_tec_admin",
        "decision": "approve_for_publication",
        "rationale": "Source contrôlée et métadonnées cohérentes.",
        "reviewed_at": "2026-11-11T10:00:00+00:00",
    }
    args.update(overrides)
    return build_evidence_review_decision(**args)


def test_approval_creates_review_event_but_never_publishes():
    event = review()
    assert event["decision"] == "approve_for_publication"
    assert event["resulting_review_status"] == "review_approved"
    assert event["publication_authorized"] is False
    assert event["publication_state"] == "draft"
    assert event["published_at"] is None


def test_source_record_is_not_mutated():
    record = pending_record()
    original = copy.deepcopy(record)
    review(record=record)
    assert record == original


@pytest.mark.parametrize("role", ["sowia_owner", "final_tec_investor_viewer", "admin", ""])
def test_rejects_roles_without_explicit_review_permission(role):
    with pytest.raises(EvidenceReviewError):
        review(reviewer_role=role)


def test_submitter_cannot_review_own_evidence():
    with pytest.raises(EvidenceReviewError, match="Séparation des tâches"):
        review(reviewer_id="submitter-1")


def test_approval_requires_https_provenance_and_timestamp():
    record = pending_record()
    record["source_url"] = "http://evidence.example/report"
    with pytest.raises(EvidenceReviewError):
        review(record=record)
    record = pending_record()
    record["observed_at"] = "2026-11-11T09:00:00"
    with pytest.raises(EvidenceReviewError):
        review(record=record)


def test_non_approval_decisions_do_not_claim_verification():
    for decision, expected in [
        ("request_changes", "changes_requested"),
        ("reject", "rejected"),
    ]:
        event = review(decision=decision)
        assert event["resulting_review_status"] == expected
        assert event["publication_state"] == "draft"
        assert event["publication_authorized"] is False


def test_requires_reason_and_timezone_aware_review_time():
    with pytest.raises(EvidenceReviewError):
        review(rationale="Non.")
    with pytest.raises(EvidenceReviewError):
        review(reviewed_at="2026-11-11T10:00:00")


def test_only_pending_draft_records_can_be_reviewed():
    record = pending_record()
    record["evidence_status"] = "verified"
    with pytest.raises(EvidenceReviewError):
        review(record=record)

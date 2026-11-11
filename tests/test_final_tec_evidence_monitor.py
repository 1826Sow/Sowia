import pytest

from final_tec_evidence_intake import EvidenceIntakeError
from final_tec_evidence_monitor import build_evidence_monitor_snapshot, prepare_evidence_batch


def valid_record(key="edge_latency"):
    return {
        "metric_key": key, "title": "Rapport latence", "category": "ai_edge_tests",
        "metric_value": 42, "unit": "ms", "source_url": "https://example.org/report",
        "observed_at": "2026-11-11T10:00:00+00:00",
        "evidence_ref": "report-001", "evidence_owner": "Equipe technique",
    }


def test_batch_always_stays_pending_draft_and_unapproved():
    row = prepare_evidence_batch([valid_record()])[0]
    assert row["evidence_status"] == "pending"
    assert row["publication_state"] == "draft"
    assert row["approved_by"] is None
    assert row["published_at"] is None


def test_rejects_duplicate_metric_keys_in_same_batch():
    with pytest.raises(EvidenceIntakeError):
        prepare_evidence_batch([valid_record(), valid_record()])


def test_rejects_non_list_and_oversized_batches():
    with pytest.raises(EvidenceIntakeError):
        prepare_evidence_batch({})
    with pytest.raises(EvidenceIntakeError):
        prepare_evidence_batch([valid_record()] * 501)


def test_rejects_self_approval_and_unknown_fields():
    record = valid_record()
    record["approved_by"] = "me"
    with pytest.raises(EvidenceIntakeError):
        prepare_evidence_batch([record])


def test_snapshot_reports_counts_and_timeline_without_claiming_live_metrics():
    rows = prepare_evidence_batch([valid_record(), valid_record("edge_cost")])
    snapshot = build_evidence_monitor_snapshot(rows)
    assert snapshot["total_submissions"] == 2
    assert snapshot["pending"] == 2
    assert snapshot["verified"] == 0
    assert snapshot["mode"] == "session_only"
    assert "pas une télémétrie temps réel" in snapshot["notice"]


def test_snapshot_handles_empty_registry():
    snapshot = build_evidence_monitor_snapshot([])
    assert snapshot["total_submissions"] == 0
    assert snapshot["timeline"] == []

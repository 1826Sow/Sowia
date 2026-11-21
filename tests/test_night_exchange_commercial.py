import pytest

from night_exchange_commercial import (
    MissionError,
    approve_mission,
    create_mission_record,
    summarize_missions,
    transition_mission,
)


def mission():
    return create_mission_record(
        mission_id="mission-001",
        requester_user_id="owner-requester",
        provider_user_id="owner-provider",
        requester_app_id="app-requester",
        provider_app_id="app-provider",
        title="Analyse documentaire",
        scope="Analyser le dossier transmis et produire une synthèse sourcée.",
        deliverable="Rapport PDF avec références et limites.",
        quoted_amount="125.50",
        currency="EUR",
        due_at="2026-12-01T17:00:00Z",
    )


def test_mission_requires_two_distinct_owner_approvals_for_same_terms():
    record = mission()
    assert record["status"] == "proposed"
    record = approve_mission(record, "owner-requester")
    assert record["status"] == "proposed"
    assert record["provider_approved_hash"] is None
    record = approve_mission(record, "owner-provider")
    assert record["status"] == "accepted"
    assert record["requester_approved_hash"] == record["terms_hash"]
    assert record["provider_approved_hash"] == record["terms_hash"]


def test_unrelated_user_cannot_approve_or_transition():
    with pytest.raises(MissionError):
        approve_mission(mission(), "intruder")
    with pytest.raises(MissionError):
        transition_mission(mission(), "intruder", "cancel")


def test_terms_tampering_invalidates_prior_approval():
    record = approve_mission(mission(), "owner-requester")
    record["terms"]["quoted_amount"] = "1.00"
    with pytest.raises(MissionError):
        approve_mission(record, "owner-provider")


def test_provider_must_follow_lifecycle_and_requester_accepts_delivery():
    record = approve_mission(mission(), "owner-requester")
    record = approve_mission(record, "owner-provider")
    with pytest.raises(MissionError):
        transition_mission(record, "owner-requester", "start")
    record = transition_mission(record, "owner-provider", "start")
    record = transition_mission(record, "owner-provider", "deliver")
    with pytest.raises(MissionError):
        transition_mission(record, "owner-provider", "accept_delivery")
    record = transition_mission(record, "owner-requester", "accept_delivery")
    assert record["status"] == "completed"


def test_cancellation_and_dispute_rules_are_bounded():
    record = transition_mission(mission(), "owner-requester", "cancel")
    assert record["status"] == "cancelled"
    with pytest.raises(MissionError):
        transition_mission(record, "owner-provider", "start")
    record = approve_mission(mission(), "owner-requester")
    record = approve_mission(record, "owner-provider")
    record = transition_mission(record, "owner-provider", "start")
    record = transition_mission(record, "owner-provider", "deliver")
    record = transition_mission(
        record, "owner-requester", "dispute", reason="Le rapport ne correspond pas au périmètre."
    )
    assert record["status"] == "disputed"


def test_quote_validation_rejects_bad_currency_and_amount():
    with pytest.raises(MissionError):
        create_mission_record(
            mission_id="m", requester_user_id="u1", provider_user_id="u2",
            requester_app_id="a1", provider_app_id="a2", title="T",
            scope="S", deliverable="D", quoted_amount="-1", currency="EUR",
        )
    with pytest.raises(MissionError):
        create_mission_record(
            mission_id="m", requester_user_id="u1", provider_user_id="u2",
            requester_app_id="a1", provider_app_id="a2", title="T",
            scope="S", deliverable="D", quoted_amount="10", currency="EURO",
        )


def test_summary_reports_quotes_not_recognized_revenue():
    record = mission()
    snapshot = summarize_missions([record, None, {"status": "cancelled"}])
    assert snapshot["mission_count"] == 2
    assert snapshot["status_counts"]["proposed"] == 1
    assert snapshot["recognized_revenue_available"] is False
    assert snapshot["payment_processing_enabled"] is False
    assert snapshot["quoted_value_by_currency"] == {"EUR": "125.50"}

def test_terms_tampering_after_acceptance_blocks_execution():
    record = approve_mission(mission(), "owner-requester")
    record = approve_mission(record, "owner-provider")
    record["terms"]["scope"] = "Périmètre remplacé après signature."
    with pytest.raises(MissionError):
        transition_mission(record, "owner-provider", "start")

from datetime import date

from relationship_advisor import recommend_next_actions


def test_overdue_events_rank_before_crm_suggestions():
    result = recommend_next_actions(
        [{"id": 1, "organization": "Alpha", "status": "À vérifier"}],
        [{"id": 9, "title": "Renouvellement", "due_date": "2027-03-01", "status": "À faire"}],
        today=date(2027, 3, 4),
    )
    assert result[0]["kind"] == "Rappel en retard"
    assert result[0]["priority"] == 1


def test_contacted_stale_lead_suggests_review_not_automatic_send():
    result = recommend_next_actions(
        [{"id": 1, "organization": "Beta", "status": "Contacté", "updated_at": "2027-02-01T10:00:00Z"}],
        [], today=date(2027, 3, 4), stale_after_days=14,
    )
    assert len(result) == 1
    assert result[0]["kind"] == "Suivi à examiner"
    assert "préférences" in result[0]["action"]
    assert result[0]["contact_authorized"] is False


def test_recent_contact_does_not_create_stale_suggestion():
    result = recommend_next_actions(
        [{"id": 1, "organization": "Gamma", "status": "Contacté", "updated_at": "2027-03-01T10:00:00Z"}],
        [], today=date(2027, 3, 4),
    )
    assert result == []


def test_replied_and_discussion_statuses_have_distinct_actions():
    result = recommend_next_actions(
        [
            {"id": 1, "organization": "Delta", "status": "Réponse reçue"},
            {"id": 2, "organization": "Epsilon", "status": "En discussion"},
        ], [], today=date(2027, 3, 4),
    )
    assert {item["kind"] for item in result} == {"Réponse à traiter", "Partenariat en discussion"}


def test_completed_cancelled_and_future_events_are_not_overdue():
    result = recommend_next_actions([], [
        {"title": "Fini", "due_date": "2027-03-01", "status": "Terminé"},
        {"title": "Annulé", "due_date": "2027-03-01", "status": "Annulé"},
        {"title": "Futur", "due_date": "2027-03-10", "status": "À faire"},
    ], today=date(2027, 3, 4))
    assert result == []


def test_results_are_bounded_and_sorted_by_priority():
    result = recommend_next_actions(
        [{"id": i, "organization": f"Org {i}", "status": "À vérifier"} for i in range(8)],
        [], today=date(2027, 3, 4), limit=3,
    )
    assert len(result) == 3
    assert [item["priority"] for item in result] == [3, 3, 3]

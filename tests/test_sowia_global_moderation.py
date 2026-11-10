import pytest

from sowia_global_moderation import (
    validate_moderation_note, validate_report_status, validate_profile_status,
)


def test_moderation_note_is_trimmed():
    assert validate_moderation_note("  décision  ") == "décision"


def test_moderation_note_limit():
    with pytest.raises(ValueError):
        validate_moderation_note("x" * 1001)


@pytest.mark.parametrize("status", ["open", "reviewing", "resolved", "dismissed"])
def test_report_statuses(status):
    assert validate_report_status(status) == status


def test_invalid_report_status():
    with pytest.raises(ValueError):
        validate_report_status("deleted")


def test_verified_profile_requires_evidence_reference():
    with pytest.raises(ValueError):
        validate_profile_status("verified")
    assert validate_profile_status("verified", "dossier interne #123") == (
        "verified", "dossier interne #123"
    )


def test_suspended_profile_status():
    assert validate_profile_status("suspended") == ("suspended", "")



def test_repeated_report_patterns_flagged_without_automatic_verdict():
    from sowia_global_moderation import summarize_report_patterns
    reports = [
        {"reported_user_id": "target-a", "reporter_id": "person-1", "status": "open"},
        {"reported_user_id": "target-a", "reporter_id": "person-2", "status": "reviewing"},
        {"reported_user_id": "target-a", "reporter_id": "person-3", "status": "open"},
        {"reported_user_id": "target-b", "reporter_id": "person-1", "status": "open"},
        {"reported_user_id": "target-a", "reporter_id": "person-4", "status": "dismissed"},
    ]
    result = summarize_report_patterns(reports)
    assert result["repeated_targets"] == [{"account_id": "target-a", "report_count": 3}]
    assert result["repeated_reporters"] == []


def test_repeated_reporter_pattern_is_flagged_for_review():
    from sowia_global_moderation import summarize_report_patterns
    reports = [
        {"reported_user_id": f"target-{i}", "reporter_id": "same-person", "status": "open"}
        for i in range(3)
    ]
    result = summarize_report_patterns(reports)
    assert result["repeated_reporters"] == [{"account_id": "same-person", "report_count": 3}]


def test_invalid_reports_do_not_break_pattern_analysis():
    from sowia_global_moderation import summarize_report_patterns
    result = summarize_report_patterns([None, {}, {"reported_user_id": "x", "status": "resolved"}])
    assert result["repeated_targets"] == []
    assert result["repeated_reporters"] == []

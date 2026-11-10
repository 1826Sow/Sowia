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

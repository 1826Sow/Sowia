import pytest

from sowia_global_notifications import (
    MESSAGES, SUPPORTED_LANGUAGES, translate, safe_notification_projection,
)


@pytest.mark.parametrize("language", SUPPORTED_LANGUAGES)
def test_every_supported_language_has_core_events(language):
    for event in (
        "connection_request_received", "connection_request_accepted",
        "connection_request_declined", "new_message",
    ):
        assert translate(event, language)


def test_unknown_language_falls_back_to_french():
    assert translate("new_message", "xx") == MESSAGES["fr"]["new_message"]


def test_unknown_event_uses_localized_title():
    assert translate("not_an_event", "en") == MESSAGES["en"]["title"]


def test_projection_excludes_private_fields():
    row = safe_notification_projection({
        "id": "n1", "event_type": "new_message", "reference_id": "m1",
        "created_at": "now", "read_at": None, "user_id": "secret",
        "email": "private@example.com",
    })
    assert "user_id" not in row
    assert "email" not in row

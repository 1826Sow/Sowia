import pytest

from sowia_global_messenger import validate_message, safe_message_projection


def test_message_is_trimmed():
    assert validate_message("  Bonjour  ") == "Bonjour"


@pytest.mark.parametrize("value", ["", "   ", None])
def test_empty_message_is_rejected(value):
    with pytest.raises(ValueError):
        validate_message(value)


def test_message_limit():
    assert len(validate_message("x" * 4000)) == 4000
    with pytest.raises(ValueError):
        validate_message("x" * 4001)


def test_projection_excludes_unapproved_fields():
    projected = safe_message_projection({
        "id": "m1", "request_id": "r1", "sender_id": "u1",
        "recipient_id": "u2", "body": "hello", "created_at": "now",
        "email": "private@example.com", "phone": "+33000000000",
    })
    assert "email" not in projected
    assert "phone" not in projected
    assert projected["body"] == "hello"

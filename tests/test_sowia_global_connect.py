from sowia_global_connect import validate_connection_message, public_request_status


def test_message_is_trimmed_and_bounded():
    assert validate_connection_message("  Bonjour, je souhaite échanger.  ") == "Bonjour, je souhaite échanger."


def test_message_requires_minimum_and_maximum_length():
    import pytest
    with pytest.raises(ValueError):
        validate_connection_message("Bonjour")
    with pytest.raises(ValueError):
        validate_connection_message("x" * 1001)


def test_public_status_does_not_expose_private_request_fields():
    result = public_request_status({"id": "r1", "status": "accepted", "message": "secret", "requester_id": "u1"})
    assert result == {"status": "accepted"}

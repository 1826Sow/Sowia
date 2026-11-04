"""Tests for cloud-storage ownership guards."""
import pytest
import cloud_storage


class User:
    id = "user-123"


def test_storage_requires_authenticated_user():
    with pytest.raises(PermissionError, match="Connexion requise"):
        cloud_storage._user_id(None)


def test_storage_uses_authenticated_subject_id():
    assert cloud_storage._user_id(User()) == "user-123"


def test_memory_input_is_validated_before_database_write():
    class Client:
        def table(self, _name):
            raise AssertionError("Database must not be called for invalid input")

    with pytest.raises(ValueError):
        cloud_storage.add_memory(Client(), User(), "   ")
    with pytest.raises(ValueError):
        cloud_storage.add_memory(Client(), User(), "x" * 1001)

from types import SimpleNamespace

import pytest
import cloud_storage


class User:
    id = "user-language-123"


class Query:
    def __init__(self):
        self.filters = []
        self.payload = None
        self.conflict = None

    def select(self, columns):
        self.columns = columns
        return self

    def upsert(self, payload, on_conflict):
        self.payload = payload
        self.conflict = on_conflict
        return self

    def eq(self, field, value):
        self.filters.append((field, value))
        return self

    def limit(self, value):
        self.limit_value = value
        return self

    def execute(self):
        return SimpleNamespace(data=[])


class Client:
    def __init__(self):
        self.query = Query()

    def table(self, name):
        assert name == "sowia_user_preferences"
        return self.query


def test_language_preference_defaults_to_french():
    client = Client()
    assert cloud_storage.get_language_preference(client, User()) == "Français"
    assert ("user_id", User.id) in client.query.filters


@pytest.mark.parametrize("language", ["Français", "English", "Español", "中文", "Deutsch", "العربية"])
def test_language_preference_upserts_supported_language_for_user(language):
    client = Client()
    cloud_storage.set_language_preference(client, User(), language)
    assert client.query.payload == {"user_id": User.id, "language": language}
    assert client.query.conflict == "user_id"


def test_language_preference_rejects_unsupported_language_before_database_write():
    class ForbiddenClient:
        def table(self, _name):
            raise AssertionError("Database must not be called")

    with pytest.raises(ValueError, match="Langue"):
        cloud_storage.set_language_preference(ForbiddenClient(), User(), "Klingon")


def test_language_preference_requires_authenticated_user():
    with pytest.raises(PermissionError, match="Connexion requise"):
        cloud_storage.get_language_preference(Client(), None)

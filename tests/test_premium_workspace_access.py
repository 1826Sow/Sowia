from types import SimpleNamespace

import pytest
import premium_access


class Query:
    def __init__(self, data=None):
        self.data = data
        self.filters = []
    def select(self, fields):
        return self
    def eq(self, field, value):
        self.filters.append((field, value))
        return self
    def maybe_single(self):
        return self
    def execute(self):
        return SimpleNamespace(data=self.data)


class Client:
    def __init__(self, data=None):
        self.query = Query(data)
    def table(self, name):
        self.table_name = name
        return self.query


class User:
    id = "user-123"


def test_personal_workspace_remains_free_without_entitlement():
    assert premium_access.require_workspace_access("personal", None, None) is None


def test_professional_workspace_requires_active_entitlement():
    with pytest.raises(PermissionError, match="accès SOW IA Premium actif"):
        premium_access.require_workspace_access("professional", Client(None), User())


def test_professional_workspace_accepts_active_entitlement():
    active = {"status": "active", "provider": "paypal"}
    assert premium_access.require_workspace_access(
        "professional", Client(active), User()
    ) == active


def test_professional_workspace_fails_closed_without_authenticated_user():
    with pytest.raises(PermissionError, match="Connexion requise"):
        premium_access.require_workspace_access("professional", Client(None), None)


@pytest.mark.parametrize("workspace_id", ["", None, "shared", "administrator", "professional-admin"])
def test_unknown_workspace_is_rejected_instead_of_falling_back_to_personal(workspace_id):
    with pytest.raises(ValueError, match="Espace de travail invalide"):
        premium_access.require_workspace_access(workspace_id, Client(None), User())


def test_workspace_name_is_normalized_before_access_check():
    active = {"status": "active", "provider": "paypal"}
    assert premium_access.require_workspace_access(
        " PROFESSIONAL ", Client(active), User()
    ) == active

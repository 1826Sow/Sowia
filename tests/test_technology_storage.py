from types import SimpleNamespace

import pytest

from technology_storage import (
    delete_all_technology_candidates,
    list_technology_candidates,
    upsert_technology_candidate,
)


class FakeQuery:
    def __init__(self):
        self.filters = []
        self.payload = None
        self.conflict = None
        self.selected = None

    def select(self, fields):
        self.selected = fields
        return self

    def eq(self, key, value):
        self.filters.append((key, value))
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, value):
        return self

    def upsert(self, payload, on_conflict=None):
        self.payload = payload
        self.conflict = on_conflict
        return self

    def delete(self):
        return self

    def execute(self):
        return SimpleNamespace(data=[self.payload] if self.payload else [])


class FakeClient:
    def __init__(self):
        self.query = FakeQuery()
        self.table_name = None

    def table(self, name):
        self.table_name = name
        return self.query


class User:
    id = "00000000-0000-0000-0000-000000000001"


def valid_values():
    return {
        "name": "Fournisseur A",
        "scores": {
            "quality": 4, "reliability": 4, "security": 4, "integration": 4,
            "cost_efficiency": 4, "international_coverage": 4, "support": 4,
            "portability": 4,
        },
        "score": 80,
        "decision": "À documenter",
        "reasons": ["Licence à vérifier"],
        "evidence": ["https://example.org/docs"],
        "compliance_verified": False,
        "compliant": True,
        "critical_incident": False,
    }


def test_upsert_is_scoped_to_authenticated_user_and_workspace():
    client = FakeClient()
    upsert_technology_candidate(client, User(), "professional", **valid_values())
    assert client.table_name == "sowia_technology_candidates"
    assert client.query.payload["user_id"] == User.id
    assert client.query.payload["workspace_id"] == "professional"
    assert client.query.conflict == "user_id,workspace_id,name"


def test_list_and_delete_are_scoped_to_user_and_workspace():
    client = FakeClient()
    list_technology_candidates(client, User(), "personal")
    assert ("user_id", User.id) in client.query.filters
    assert ("workspace_id", "personal") in client.query.filters

    client = FakeClient()
    delete_all_technology_candidates(client, User(), "professional")
    assert ("user_id", User.id) in client.query.filters
    assert ("workspace_id", "professional") in client.query.filters


def test_missing_user_and_invalid_workspace_are_rejected():
    client = FakeClient()
    with pytest.raises(PermissionError):
        list_technology_candidates(client, SimpleNamespace(id=None))
    with pytest.raises(ValueError):
        list_technology_candidates(client, User(), "shared")

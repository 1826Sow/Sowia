from financial_audit import load_user_financial_audit_events, present_audit_events


class Query:
    def __init__(self, client):
        self.client = client

    def select(self, fields):
        self.client.selected = fields
        return self

    def eq(self, key, value):
        self.client.filters.append((key, value))
        return self

    def order(self, key, desc=False):
        self.client.ordering = (key, desc)
        return self

    def limit(self, value):
        self.client.limit = value
        return self

    def execute(self):
        return type("Result", (), {"data": self.client.rows})()


class Client:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.filters = []

    def table(self, name):
        assert name == "sowia_financial_audit_log"
        return Query(self)


def test_audit_reader_is_scoped_to_user_and_bounded():
    client = Client([{"event_id": "e1", "user_id": "u1"}])
    rows = load_user_financial_audit_events(client, "u1", limit=25)
    assert rows[0]["event_id"] == "e1"
    assert ("user_id", "u1") in client.filters
    assert client.ordering == ("changed_at", True)
    assert client.limit == 25


def test_audit_reader_rejects_missing_identity_and_invalid_limits():
    import pytest

    with pytest.raises(PermissionError):
        load_user_financial_audit_events(Client(), "")
    with pytest.raises(ValueError):
        load_user_financial_audit_events(Client(), "u1", limit=True)
    with pytest.raises(ValueError):
        load_user_financial_audit_events(Client(), "u1", limit=501)


def test_presentation_omits_full_snapshots_and_user_identifiers():
    presented = present_audit_events([{
        "event_id": "e1",
        "user_id": "private-user-id",
        "actor_id": "actor-id",
        "actor_role": "service_role",
        "operation": "UPDATE",
        "changed_at": "2026-11-10T10:00:00Z",
        "ledger_row_id": "ledger-1",
        "before_data": {"status": "confirmed", "gross_amount": "10.00", "gross_currency": "EUR", "reference_amount_eur": "10.00", "tax_amount_eur": "0.80"},
        "after_data": {"status": "manual_review", "gross_amount": "10.00", "gross_currency": "EUR", "reference_amount_eur": "11.00", "tax_amount_eur": "0.90"},
    }])
    assert presented[0]["Statut avant"] == "confirmed"
    assert presented[0]["Statut après"] == "manual_review"
    assert presented[0]["Référence EUR avant"] == "10.00"
    assert presented[0]["Référence EUR après"] == "11.00"
    assert presented[0]["Taxe EUR avant"] == "0.80"
    assert presented[0]["Taxe EUR après"] == "0.90"
    assert "private-user-id" not in str(presented)
    assert "actor-id" not in str(presented)

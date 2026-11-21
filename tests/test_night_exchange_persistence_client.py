from types import SimpleNamespace

import pytest

import cloud_storage


class FakeResult:
    def __init__(self, data):
        self.data = data


class FakeRpc:
    def __init__(self, name, params, result):
        self.name = name
        self.params = params
        self.result = result

    def execute(self):
        return FakeResult(self.result)


class FakeClient:
    def __init__(self):
        self.calls = []

    def rpc(self, name, params):
        call = FakeRpc(name, params, "ok")
        self.calls.append(call)
        return call


def test_create_mission_uses_server_rpc_and_normalizes_quote():
    client = FakeClient()
    user = SimpleNamespace(id="user-a")
    result = cloud_storage.create_night_exchange_mission(
        client, user, "provider-app", "requester-app",
        "Analyse de dossier", "Périmètre convenu", "Rapport PDF",
        "125.50", "eur", "2026-12-01T17:00:00Z",
    )
    assert result == "ok"
    assert client.calls[0].name == "sowia_nex_create_mission"
    assert client.calls[0].params["p_quoted_amount"] == "125.50"
    assert client.calls[0].params["p_currency"] == "EUR"


def test_mission_approval_and_transition_use_guarded_server_rpcs():
    client = FakeClient()
    user = SimpleNamespace(id="user-a")
    cloud_storage.approve_night_exchange_mission(client, user, "mission-1")
    cloud_storage.transition_night_exchange_mission(
        client, user, "mission-1", "dispute", "Livrable incomplet"
    )
    assert [call.name for call in client.calls] == [
        "sowia_nex_approve_mission", "sowia_nex_transition_mission"
    ]


@pytest.mark.parametrize("amount", ["0", "-2", "NaN", "Infinity", "not-money"])
def test_create_mission_rejects_invalid_quote_before_rpc(amount):
    client = FakeClient()
    with pytest.raises(ValueError):
        cloud_storage.create_night_exchange_mission(
            client, SimpleNamespace(id="user-a"), "provider-app", "requester-app",
            "Titre", "Périmètre", "Livrable", amount, "EUR",
        )
    assert client.calls == []


def test_transition_rejects_unknown_actions_and_missing_dispute_reason():
    client = FakeClient()
    user = SimpleNamespace(id="user-a")
    with pytest.raises(ValueError):
        cloud_storage.transition_night_exchange_mission(
            client, user, "mission-1", "pay"
        )
    with pytest.raises(ValueError):
        cloud_storage.transition_night_exchange_mission(
            client, user, "mission-1", "dispute", " "
        )
    assert client.calls == []


def test_mission_operations_require_authenticated_user():
    client = FakeClient()
    with pytest.raises(PermissionError):
        cloud_storage.approve_night_exchange_mission(
            client, SimpleNamespace(id=None), "mission-1"
        )
    assert client.calls == []

def test_admin_verification_requires_admin_claim_and_uses_audited_rpc():
    client = FakeClient()
    admin = SimpleNamespace(id="admin-user", app_metadata={"sowia_admin": True})
    result = cloud_storage.admin_verify_night_exchange_app(
        client, admin, "app-1", "verified", "verified", "passed",
        "verified", "Contrôle documentaire effectué",
    )
    assert result == "ok"
    assert client.calls[0].name == "sowia_admin_verify_nex_app"
    assert client.calls[0].params["p_publisher_signature_status"] == "verified"

    ordinary_user = SimpleNamespace(id="member-user", app_metadata={})
    with pytest.raises(PermissionError):
        cloud_storage.admin_verify_night_exchange_app(
            client, ordinary_user, "app-1", "verified", "verified",
            "passed", "verified",
        )


def test_admin_verification_rejects_invalid_attestation_before_rpc():
    client = FakeClient()
    admin = SimpleNamespace(id="admin-user", app_metadata={"role": "admin"})
    with pytest.raises(ValueError):
        cloud_storage.admin_verify_night_exchange_app(
            client, admin, "app-1", "verified", "verified",
            "passed", "signature_unknown",
        )
    assert client.calls == []

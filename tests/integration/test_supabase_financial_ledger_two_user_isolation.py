"""Live two-user RLS/privilege checks for the SOWIA financial ledger.

Run only against a dedicated Supabase test project with two dedicated accounts.
The test uses the public anon key and user JWTs only; it never uses service_role
and never writes, updates, or deletes financial rows.
"""
import os

import pytest
import requests


_REQUIRED = (
    "SOWIA_TEST_SUPABASE_URL",
    "SOWIA_TEST_SUPABASE_ANON_KEY",
    "SOWIA_TEST_USER_A_EMAIL",
    "SOWIA_TEST_USER_A_PASSWORD",
    "SOWIA_TEST_USER_B_EMAIL",
    "SOWIA_TEST_USER_B_PASSWORD",
)
_MISSING = [name for name in _REQUIRED if not os.getenv(name)]
pytestmark = pytest.mark.skipif(
    bool(_MISSING),
    reason="Dedicated live Supabase test credentials are not configured",
)


class SupabaseUser:
    def __init__(self, url, anon_key, email, password):
        self.url = url.rstrip("/")
        self.anon_key = anon_key
        response = requests.post(
            f"{self.url}/auth/v1/token",
            params={"grant_type": "password"},
            headers={"apikey": anon_key, "Content-Type": "application/json"},
            json={"email": email, "password": password},
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        self.user_id = payload["user"]["id"]
        self.headers = {
            "apikey": anon_key,
            "Authorization": f"Bearer {payload['access_token']}",
            "Content-Type": "application/json",
        }

    def request(self, method, params=None, payload=None, headers=None):
        request_headers = dict(self.headers)
        if headers:
            request_headers.update(headers)
        return requests.request(
            method,
            f"{self.url}/rest/v1/sowia_financial_transactions",
            headers=request_headers,
            params=params,
            json=payload,
            timeout=20,
        )


@pytest.fixture(scope="module")
def accounts():
    url = os.environ["SOWIA_TEST_SUPABASE_URL"]
    anon_key = os.environ["SOWIA_TEST_SUPABASE_ANON_KEY"]
    account_a = SupabaseUser(
        url, anon_key,
        os.environ["SOWIA_TEST_USER_A_EMAIL"],
        os.environ["SOWIA_TEST_USER_A_PASSWORD"],
    )
    account_b = SupabaseUser(
        url, anon_key,
        os.environ["SOWIA_TEST_USER_B_EMAIL"],
        os.environ["SOWIA_TEST_USER_B_PASSWORD"],
    )
    assert account_a.user_id != account_b.user_id
    return account_a, account_b


def _fixture_payment_id():
    return os.getenv("SOWIA_TEST_FINANCIAL_FIXTURE_PAYMENT_ID")


def test_financial_ledger_is_not_readable_without_authentication():
    url = os.environ["SOWIA_TEST_SUPABASE_URL"].rstrip("/")
    anon_key = os.environ["SOWIA_TEST_SUPABASE_ANON_KEY"]
    response = requests.get(
        f"{url}/rest/v1/sowia_financial_transactions",
        headers={"apikey": anon_key, "Accept": "application/json"},
        params={"select": "id", "limit": "1"},
        timeout=20,
    )
    assert response.status_code in (401, 403), (
        "Anonymous access to the financial ledger must be denied; "
        f"received HTTP {response.status_code}"
    )


def test_authenticated_users_cannot_insert_financial_ledger_rows(accounts):
    account_a, _ = accounts
    payload = {
        "user_id": account_a.user_id,
        "provider": "sowia_rls_test",
        "provider_payment_id": "must-not-be-inserted-by-client",
        "transaction_type": "payment",
        "status": "manual_review",
        "gross_amount": "0.01",
        "gross_currency": "EUR",
        "occurred_at": "2026-01-01T00:00:00Z",
    }
    response = account_a.request(
        "POST",
        params={"select": "id"},
        payload=payload,
        headers={"Prefer": "return=representation"},
    )
    assert response.status_code in (401, 403), (
        "Authenticated client must not insert ledger rows; "
        f"received HTTP {response.status_code}"
    )


def test_two_users_cannot_read_each_others_financial_rows(accounts):
    payment_id = _fixture_payment_id()
    if not payment_id:
        pytest.skip(
            "Seed a synthetic owner-A ledger row in the isolated test project "
            "and set SOWIA_TEST_FINANCIAL_FIXTURE_PAYMENT_ID"
        )

    account_a, account_b = accounts
    params = {
        "provider": "eq.paypal",
        "provider_payment_id": f"eq.{payment_id}",
        "transaction_type": "eq.payment",
        "select": "id,user_id,provider_payment_id,gross_amount,gross_currency",
        "limit": "2",
    }
    visible_to_a = account_a.request("GET", params=params)
    visible_to_b = account_b.request("GET", params=params)
    visible_to_a.raise_for_status()
    visible_to_b.raise_for_status()

    rows_a = visible_to_a.json()
    rows_b = visible_to_b.json()
    assert len(rows_a) == 1, "Account A must see exactly its seeded fixture row"
    assert rows_a[0]["user_id"] == account_a.user_id
    assert rows_a[0]["provider_payment_id"] == payment_id
    assert rows_b == [], "Account B must not see Account A's financial fixture"


def test_authenticated_clients_cannot_update_or_delete_ledger_rows(accounts):
    payment_id = _fixture_payment_id()
    if not payment_id:
        pytest.skip(
            "Seed a synthetic owner-A ledger row in the isolated test project "
            "and set SOWIA_TEST_FINANCIAL_FIXTURE_PAYMENT_ID"
        )

    account_a, account_b = accounts
    filter_params = {
        "provider": "eq.paypal",
        "provider_payment_id": f"eq.{payment_id}",
        "transaction_type": "eq.payment",
    }
    update = account_a.request(
        "PATCH",
        params=filter_params,
        payload={"gross_amount": "0.02"},
        headers={"Prefer": "return=representation"},
    )
    delete = account_a.request("DELETE", params=filter_params)
    assert update.status_code in (401, 403), (
        "Authenticated client must not update ledger rows; "
        f"received HTTP {update.status_code}"
    )
    assert delete.status_code in (401, 403), (
        "Authenticated client must not delete ledger rows; "
        f"received HTTP {delete.status_code}"
    )

    # The second account also cannot mutate a row it cannot own or read.
    other_update = account_b.request(
        "PATCH",
        params=filter_params,
        payload={"gross_amount": "0.03"},
        headers={"Prefer": "return=representation"},
    )
    other_delete = account_b.request("DELETE", params=filter_params)
    assert other_update.status_code in (401, 403)
    assert other_delete.status_code in (401, 403)

    # Verify that the owner-A fixture remains present and unchanged.
    check = account_a.request(
        "GET",
        params={**filter_params, "select": "user_id,provider_payment_id,gross_amount"},
    )
    check.raise_for_status()
    rows = check.json()
    assert len(rows) == 1
    assert rows[0]["user_id"] == account_a.user_id
    assert rows[0]["provider_payment_id"] == payment_id
    assert str(rows[0]["gross_amount"]) == "0.010000000000"

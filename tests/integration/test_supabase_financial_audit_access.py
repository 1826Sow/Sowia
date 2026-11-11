"""Live Supabase check: authenticated users cannot read the financial audit log.

Run only against a dedicated Supabase test project with two dedicated users.
This test uses the public anon key and authenticated JWTs only; never service_role.
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


def _authenticated_headers(url, anon_key, email, password):
    response = requests.post(
        f"{url.rstrip('/')}/auth/v1/token",
        params={"grant_type": "password"},
        headers={"apikey": anon_key, "Content-Type": "application/json"},
        json={"email": email, "password": password},
        timeout=20,
    )
    response.raise_for_status()
    access_token = response.json()["access_token"]
    return {
        "apikey": anon_key,
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }


@pytest.mark.parametrize("account", ["A", "B"])
def test_authenticated_accounts_cannot_read_financial_audit_log(account):
    """The audit table must remain server-only after its migration is applied."""
    url = os.environ["SOWIA_TEST_SUPABASE_URL"].rstrip("/")
    anon_key = os.environ["SOWIA_TEST_SUPABASE_ANON_KEY"]
    email = os.environ[f"SOWIA_TEST_USER_{account}_EMAIL"]
    password = os.environ[f"SOWIA_TEST_USER_{account}_PASSWORD"]
    headers = _authenticated_headers(url, anon_key, email, password)

    response = requests.get(
        f"{url}/rest/v1/sowia_financial_audit_log",
        headers=headers,
        params={"select": "event_id", "limit": "1"},
        timeout=20,
    )

    assert response.status_code in (401, 403), (
        "Authenticated users must not read the server-only financial audit log; "
        f"received HTTP {response.status_code}"
    )

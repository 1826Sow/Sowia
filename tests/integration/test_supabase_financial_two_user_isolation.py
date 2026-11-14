"""Live two-account RLS checks for financial and PayPal subscription rows.

Fixtures are created/deleted with the service-role key of a disposable test
project only. Every assertion about client access uses anon-key authenticated
sessions, never the service-role key.
"""
import os
import uuid
from datetime import datetime, timezone
from urllib.parse import urlsplit

import pytest
import requests


_CONFIRMATION = "I_CONFIRM_THIS_IS_A_DEDICATED_SOWIA_TEST_PROJECT"
_REQUIRED = (
    "SOWIA_TEST_SUPABASE_URL",
    "SOWIA_TEST_SUPABASE_ANON_KEY",
    "SOWIA_TEST_SUPABASE_SERVICE_ROLE_KEY",
    "SOWIA_TEST_USER_A_EMAIL",
    "SOWIA_TEST_USER_A_PASSWORD",
    "SOWIA_TEST_USER_B_EMAIL",
    "SOWIA_TEST_USER_B_PASSWORD",
    "SOWIA_TEST_PROJECT_CONFIRMATION",
)
_MISSING = [name for name in _REQUIRED if not os.getenv(name)]
if not _MISSING and os.environ["SOWIA_TEST_PROJECT_CONFIRMATION"] != _CONFIRMATION:
    raise RuntimeError("Refusing live tests: explicit dedicated-test-project confirmation is missing")
pytestmark = pytest.mark.skipif(
    bool(_MISSING),
    reason="Dedicated live Supabase test-project credentials are not configured",
)


def _validated_supabase_url(value):
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or not parsed.hostname.endswith(".supabase.co")
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in ("", "/")
    ):
        raise ValueError("Refusing live tests: URL must be a plain HTTPS hosted Supabase project URL")
    return value.rstrip("/")


class ApiSession:
    def __init__(self, url, api_key, bearer=None):
        self.url = _validated_supabase_url(url)
        self.http = requests.Session()
        self.headers = {"apikey": api_key, "Content-Type": "application/json"}
        if bearer:
            self.headers["Authorization"] = f"Bearer {bearer}"

    def request(self, method, path, *, params=None, payload=None, prefer=None):
        headers = dict(self.headers)
        if prefer:
            headers["Prefer"] = prefer
        return self.http.request(
            method,
            f"{self.url}{path}",
            headers=headers,
            params=params,
            json=payload,
            timeout=20,
        )


def _login(url, anon_key, email, password):
    api = ApiSession(url, anon_key)
    response = api.request(
        "POST",
        "/auth/v1/token",
        params={"grant_type": "password"},
        payload={"email": email, "password": password},
    )
    if not response.ok:
        try:
            error = response.json()
        except ValueError:
            error = {}
        reason = error.get("msg") or error.get("message") or error.get("error_description") or error.get("error") or "no safe error detail returned"
        raise RuntimeError(f"Supabase test-user login failed (HTTP {response.status_code}): {reason}")
    payload = response.json()
    return ApiSession(url, anon_key, payload["access_token"]), payload["user"]["id"]


@pytest.mark.parametrize(
    ("table", "select_columns", "owner_payload", "forged_payload"),
    [
        (
            "sowia_financial_transactions",
            "id,user_id,provider,provider_payment_id,transaction_type",
            lambda owner, token: {
                "user_id": owner,
                "provider": "sowia-rls-test",
                "provider_payment_id": token,
                "transaction_type": "payment",
                "status": "confirmed",
                "gross_amount": 1,
                "gross_currency": "EUR",
                "occurred_at": datetime.now(timezone.utc).isoformat(),
            },
            lambda owner, token: {
                "user_id": owner,
                "provider": "sowia-rls-test",
                "provider_payment_id": token + "-forged",
                "transaction_type": "payment",
                "status": "confirmed",
                "gross_amount": 1,
                "gross_currency": "EUR",
                "occurred_at": datetime.now(timezone.utc).isoformat(),
            },
        ),
        (
            "sowia_subscriptions",
            "id,user_id,paypal_subscription_id,status",
            lambda owner, token: {
                "user_id": owner,
                "provider": "paypal",
                "paypal_subscription_id": "I-" + token[:24].upper(),
                "paypal_plan_id": "P-SOWIARLSTEST",
                "status": "past_due",
                "currency": "EUR",
                "amount": 9.90,
            },
            lambda owner, token: {
                "user_id": owner,
                "provider": "paypal",
                "paypal_subscription_id": "I-" + (token + "FORGED")[:24].upper(),
                "paypal_plan_id": "P-SOWIARLSTEST",
                "status": "past_due",
                "currency": "EUR",
                "amount": 9.90,
            },
        ),
    ],
)
def test_financial_and_subscription_rows_are_owner_read_only(
    table, select_columns, owner_payload, forged_payload
):
    """A sees its row; B cannot read, forge ownership, or delete it."""
    url = os.environ["SOWIA_TEST_SUPABASE_URL"]
    anon_key = os.environ["SOWIA_TEST_SUPABASE_ANON_KEY"]
    service_key = os.environ["SOWIA_TEST_SUPABASE_SERVICE_ROLE_KEY"]
    account_a, user_a = _login(
        url, anon_key,
        os.environ["SOWIA_TEST_USER_A_EMAIL"],
        os.environ["SOWIA_TEST_USER_A_PASSWORD"],
    )
    account_b, user_b = _login(
        url, anon_key,
        os.environ["SOWIA_TEST_USER_B_EMAIL"],
        os.environ["SOWIA_TEST_USER_B_PASSWORD"],
    )
    assert user_a != user_b

    admin = ApiSession(url, service_key, service_key)
    token = uuid.uuid4().hex.upper()
    fixture_id = None
    try:
        seeded = admin.request(
            "POST",
            f"/rest/v1/{table}",
            params={"select": "id"},
            payload=owner_payload(user_a, token),
            prefer="return=representation",
        )
        seeded.raise_for_status()
        rows = seeded.json()
        assert rows, f"Service-role fixture insert returned no row for {table}"
        fixture_id = rows[0]["id"]

        row_filter = {"id": f"eq.{fixture_id}", "select": select_columns}
        visible_a = account_a.request(
            "GET", f"/rest/v1/{table}", params=row_filter
        )
        visible_a.raise_for_status()
        assert any(str(row["id"]) == str(fixture_id) for row in visible_a.json())

        visible_b = account_b.request(
            "GET", f"/rest/v1/{table}", params=row_filter
        )
        visible_b.raise_for_status()
        assert not any(str(row["id"]) == str(fixture_id) for row in visible_b.json())

        forged = account_b.request(
            "POST",
            f"/rest/v1/{table}",
            payload=forged_payload(user_a, token),
            prefer="return=representation",
        )
        assert forged.status_code in (401, 403), (
            f"Authenticated B unexpectedly wrote to {table}: HTTP {forged.status_code}"
        )

        deletion = account_b.request(
            "DELETE",
            f"/rest/v1/{table}",
            params={"id": f"eq.{fixture_id}"},
        )
        assert deletion.status_code in (200, 204, 401, 403)
        owner_after = account_a.request(
            "GET", f"/rest/v1/{table}", params=row_filter
        )
        owner_after.raise_for_status()
        assert any(str(row["id"]) == str(fixture_id) for row in owner_after.json())
    finally:
        if fixture_id is not None:
            cleanup = admin.request(
                "DELETE",
                f"/rest/v1/{table}",
                params={"id": f"eq.{fixture_id}"},
            )
            cleanup.raise_for_status()

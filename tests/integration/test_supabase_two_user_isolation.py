"""Opt-in RLS integration tests for the current SOW IA Supabase schema.

Run only against a dedicated Supabase test project and dedicated test accounts.
The tests use the public anon key and authenticated user JWTs, never service_role.
"""
import os
import uuid

import pytest
import requests


_REQUIRED = (
    "SOWIA_TEST_SUPABASE_URL",
    "SOWIA_TEST_SUPABASE_ANON_KEY",
    "SOWIA_TEST_USER_A_EMAIL",
    "SOWIA_TEST_USER_A_PASSWORD",
    "SOWIA_TEST_USER_B_EMAIL",
    "SOWIA_TEST_USER_B_PASSWORD",
    "SOWIA_TEST_PROJECT_CONFIRMATION",
)
_MISSING = [name for name in _REQUIRED if not os.getenv(name)]
_CONFIRMATION = "I_CONFIRM_THIS_IS_A_DEDICATED_SOWIA_TEST_PROJECT"
if not _MISSING and os.environ["SOWIA_TEST_PROJECT_CONFIRMATION"] != _CONFIRMATION:
    raise RuntimeError("Refusing live tests: explicit dedicated-test-project confirmation is missing")
pytestmark = pytest.mark.skipif(
    bool(_MISSING),
    reason="Dedicated live Supabase test credentials are not configured",
)


class SupabaseTestSession:
    def __init__(self, url, anon_key, email, password):
        self.url = url.rstrip("/")
        self.anon_key = anon_key
        self.http = requests.Session()
        response = self.http.post(
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

    def table(self, method, table_name, params=None, payload=None, prefer=None):
        if table_name not in {"sowia_messages", "sowia_memory_items"}:
            raise ValueError("Unsupported current SOW IA integration table")
        headers = dict(self.headers)
        if prefer:
            headers["Prefer"] = prefer
        response = self.http.request(
            method,
            f"{self.url}/rest/v1/{table_name}",
            headers=headers,
            params=params,
            json=payload,
            timeout=20,
        )
        response.raise_for_status()
        return response.json() if response.content else []


@pytest.mark.parametrize(
    ("table_name", "payload_factory", "select_columns", "marker_column"),
    [
        (
            "sowia_messages",
            lambda owner, marker: {
                "user_id": owner,
                "session_id": marker,
                "role": "user",
                "content": marker,
                "workspace_id": "personal",
            },
            "id,user_id,session_id,content,workspace_id",
            "content",
        ),
        (
            "sowia_memory_items",
            lambda owner, marker: {
                "user_id": owner,
                "content": marker,
                "workspace_id": "personal",
            },
            "id,user_id,content,workspace_id",
            "content",
        ),
    ],
)
def test_private_rows_are_isolated_between_two_authenticated_users(
    table_name, payload_factory, select_columns, marker_column
):
    """Verify owner-only SELECT/INSERT/DELETE using real authenticated sessions."""
    url = os.environ["SOWIA_TEST_SUPABASE_URL"]
    anon_key = os.environ["SOWIA_TEST_SUPABASE_ANON_KEY"]
    account_a = SupabaseTestSession(
        url, anon_key,
        os.environ["SOWIA_TEST_USER_A_EMAIL"],
        os.environ["SOWIA_TEST_USER_A_PASSWORD"],
    )
    account_b = SupabaseTestSession(
        url, anon_key,
        os.environ["SOWIA_TEST_USER_B_EMAIL"],
        os.environ["SOWIA_TEST_USER_B_PASSWORD"],
    )
    assert account_a.user_id != account_b.user_id

    marker = "sowia-rls-" + uuid.uuid4().hex
    row_id = None
    try:
        inserted = account_a.table(
            "POST",
            table_name,
            params={"select": "id"},
            payload=payload_factory(account_a.user_id, marker),
            prefer="return=representation",
        )
        assert inserted, f"Account A could not create a test row in {table_name}"
        row_id = inserted[0]["id"]
        row_filter = f"eq.{row_id}"

        visible_to_a = account_a.table(
            "GET", table_name,
            params={"id": row_filter, "select": select_columns},
        )
        visible_to_b = account_b.table(
            "GET", table_name,
            params={"id": row_filter, "select": select_columns},
        )
        assert any(row["id"] == row_id for row in visible_to_a)
        assert not any(row["id"] == row_id for row in visible_to_b)

        # B cannot create a row that claims ownership by A.
        forged = account_b.http.post(
            f"{url.rstrip('/')}/rest/v1/{table_name}",
            headers={**account_b.headers, "Prefer": "return=representation"},
            json=payload_factory(account_a.user_id, marker + "-forged"),
            timeout=20,
        )
        assert forged.status_code in (401, 403), (
            f"RLS should reject cross-owner INSERT into {table_name}; "
            f"received HTTP {forged.status_code}"
        )

        # B's DELETE must not remove A's row.
        account_b.table("DELETE", table_name, params={"id": row_filter})
        still_visible_to_a = account_a.table(
            "GET", table_name,
            params={"id": row_filter, "select": select_columns},
        )
        assert any(
            row["id"] == row_id and row.get(marker_column) == marker
            for row in still_visible_to_a
        )
    finally:
        if row_id is not None:
            account_a.table(
                "DELETE",
                table_name,
                params={
                    "id": f"eq.{row_id}",
                    "user_id": f"eq.{account_a.user_id}",
                },
            )

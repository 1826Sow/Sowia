"""Opt-in live RLS test using two dedicated Supabase test accounts.

Uses the Supabase HTTPS Auth and REST endpoints directly. This avoids importing
the SDK package, whose supabase_auth dependency name collides with this
repository's local supabase_auth.py module.
"""
import os
import uuid
from urllib.parse import quote

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
    reason="Live Supabase isolation test: dedicated test-account variables are not configured",
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
        self.access_token = payload["access_token"]
        self.headers = {
            "apikey": anon_key,
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def table(self, method, params=None, payload=None, prefer=None, table_name="sowia_documents"):
        if table_name not in {
            "sowia_documents",
            "sowia_memory_items",
            "sowia_messages",
            "sowia_comparison_history",
        }:
            raise ValueError("Unsupported integration-test table")
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


def test_documents_are_isolated_between_two_authenticated_users():
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

    marker = "sowia-rls-test-" + uuid.uuid4().hex
    document_id = None
    try:
        inserted = account_a.table(
            "POST",
            params={"select": "id"},
            payload={
                "user_id": account_a.user_id,
                "title": marker,
                "filename": marker + ".txt",
                "extracted_text": "Private RLS isolation test",
                "text_length": len("Private RLS isolation test"),
                "category": "Autres",
                "folder": "Général",
            },
            prefer="return=representation",
        )
        assert inserted, "Account A could not create its isolated test row"
        document_id = inserted[0]["id"]
        row_filter = f"eq.{document_id}"

        visible_to_a = account_a.table(
            "GET", params={"id": row_filter, "select": "id,title"}
        )
        visible_to_b = account_b.table(
            "GET", params={"id": row_filter, "select": "id,title"}
        )
        assert any(row["id"] == document_id for row in visible_to_a)
        assert not any(row["id"] == document_id for row in visible_to_b)

        # B cannot create a row pretending to belong to A.
        response = account_b.http.post(
            f"{url.rstrip('/')}/rest/v1/sowia_documents",
            headers={**account_b.headers, "Prefer": "return=representation"},
            json={
                "user_id": account_a.user_id,
                "title": marker + "-forged",
                "filename": marker + "-forged.txt",
                "extracted_text": "Must be rejected by RLS",
                "text_length": len("Must be rejected by RLS"),
                "category": "Autres",
                "folder": "Général",
            },
            timeout=20,
        )
        assert response.status_code in (401, 403), (
            "RLS should reject an insert owned by another user; "
            f"received HTTP {response.status_code}"
        )

        # B's update/delete requests must not affect A's row.
        account_b.table(
            "PATCH",
            params={"id": row_filter},
            payload={"title": marker + "-tampered"},
            prefer="return=representation",
        )
        account_b.table("DELETE", params={"id": row_filter})

        still_owned_by_a = account_a.table(
            "GET", params={"id": row_filter, "select": "id,title"}
        )
        assert any(
            row["id"] == document_id and row["title"] == marker
            for row in still_owned_by_a
        )
    finally:
        if document_id is not None:
            account_a.table(
                "DELETE",
                params={
                    "id": f"eq.{document_id}",
                    "user_id": f"eq.{account_a.user_id}",
                },
            )



@pytest.mark.parametrize(
    ("table_name", "payload_factory", "select_columns"),
    [
        (
            "sowia_memory_items",
            lambda owner, marker: {
                "user_id": owner,
                "content": marker,
            },
            "id,content",
        ),
        (
            "sowia_messages",
            lambda owner, marker: {
                "user_id": owner,
                "session_id": marker,
                "role": "user",
                "content": "Private conversation RLS test",
            },
            "id,session_id,content",
        ),
        (
            "sowia_comparison_history",
            lambda owner, marker: {
                "user_id": owner,
                "report": {"integration_test": marker},
            },
            "id,report",
        ),
    ],
)
def test_private_data_tables_are_isolated_between_two_users(
    table_name, payload_factory, select_columns
):
    """Check SELECT/INSERT/DELETE RLS on memory, messages and comparison history."""
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

    marker = "sowia-private-rls-" + uuid.uuid4().hex
    row_id = None
    try:
        inserted = account_a.table(
            "POST",
            table_name=table_name,
            params={"select": "id"},
            payload=payload_factory(account_a.user_id, marker),
            prefer="return=representation",
        )
        assert inserted, f"Account A could not create a test row in {table_name}"
        row_id = inserted[0]["id"]
        row_filter = f"eq.{row_id}"

        visible_to_a = account_a.table(
            "GET",
            table_name=table_name,
            params={"id": row_filter, "select": select_columns},
        )
        visible_to_b = account_b.table(
            "GET",
            table_name=table_name,
            params={"id": row_filter, "select": select_columns},
        )
        assert any(row["id"] == row_id for row in visible_to_a)
        assert not any(row["id"] == row_id for row in visible_to_b)

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

        account_b.table(
            "DELETE",
            table_name=table_name,
            params={"id": row_filter},
        )
        still_visible_to_a = account_a.table(
            "GET",
            table_name=table_name,
            params={"id": row_filter, "select": select_columns},
        )
        assert any(row["id"] == row_id for row in still_visible_to_a)
    finally:
        if row_id is not None:
            account_a.table(
                "DELETE",
                table_name=table_name,
                params={
                    "id": f"eq.{row_id}",
                    "user_id": f"eq.{account_a.user_id}",
                },
            )

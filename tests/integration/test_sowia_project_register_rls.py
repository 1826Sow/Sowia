"""Real two-account RLS checks for the SOW IA project register.

Only run against a dedicated Supabase test project and two non-Premium test users.
The project table intentionally has no DELETE policy; each synthetic row is
soft-archived and can be removed later by an administrator in the test project.
"""
import os
import uuid
from urllib.parse import urlsplit

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
    raise RuntimeError("Refusing live tests without dedicated-test-project confirmation")
pytestmark = pytest.mark.skipif(
    bool(_MISSING),
    reason="Dedicated live Supabase test credentials are not configured",
)


def _project_url():
    value = os.environ["SOWIA_TEST_SUPABASE_URL"]
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
        raise ValueError("Refusing live tests: expected a plain HTTPS Supabase project URL")
    return value.rstrip("/")


class Account:
    def __init__(self, url, anon_key, email, password):
        self.url = url
        self.http = requests.Session()
        response = self.http.post(
            f"{url}/auth/v1/token",
            params={"grant_type": "password"},
            headers={"apikey": anon_key, "Content-Type": "application/json"},
            json={"email": email, "password": password},
            timeout=20,
            allow_redirects=False,
        )
        response.raise_for_status()
        payload = response.json()
        self.user_id = payload["user"]["id"]
        self.headers = {
            "apikey": anon_key,
            "Authorization": f"Bearer {payload['access_token']}",
            "Content-Type": "application/json",
        }

    def request(self, method, params=None, payload=None):
        return self.http.request(
            method,
            f"{self.url}/rest/v1/sowia_projects",
            headers={**self.headers, "Prefer": "return=representation"},
            params=params,
            json=payload,
            timeout=20,
            allow_redirects=False,
        )


def test_project_register_is_owner_scoped_and_professional_access_is_gated():
    url = _project_url()
    anon_key = os.environ["SOWIA_TEST_SUPABASE_ANON_KEY"]
    account_a = Account(
        url, anon_key,
        os.environ["SOWIA_TEST_USER_A_EMAIL"],
        os.environ["SOWIA_TEST_USER_A_PASSWORD"],
    )
    account_b = Account(
        url, anon_key,
        os.environ["SOWIA_TEST_USER_B_EMAIL"],
        os.environ["SOWIA_TEST_USER_B_PASSWORD"],
    )
    assert account_a.user_id != account_b.user_id

    marker = "SOWIA RLS TEST " + uuid.uuid4().hex
    inserted_id = None
    try:
        created = account_a.request(
            "POST",
            params={"select": "id,user_id,title,workspace_id,status"},
            payload={
                "user_id": account_a.user_id,
                "workspace_id": "personal",
                "title": marker,
                "description": "Synthetic integration-test row",
                "status": "À tester",
            },
        )
        created.raise_for_status()
        rows = created.json()
        assert len(rows) == 1
        inserted_id = rows[0]["id"]
        assert rows[0]["user_id"] == account_a.user_id

        row_filter = {"id": f"eq.{inserted_id}", "select": "id,user_id,title,workspace_id"}
        own_row = account_a.request("GET", params=row_filter)
        own_row.raise_for_status()
        assert len(own_row.json()) == 1

        hidden_from_b = account_b.request("GET", params=row_filter)
        hidden_from_b.raise_for_status()
        assert hidden_from_b.json() == []

        forged_insert = account_b.request(
            "POST",
            payload={
                "user_id": account_a.user_id,
                "workspace_id": "personal",
                "title": marker + " FORGED",
                "description": "Must be rejected by RLS",
                "status": "En cours",
            },
        )
        assert forged_insert.status_code in (401, 403), (
            "RLS must reject a project insert that claims another user's ID; "
            f"received HTTP {forged_insert.status_code}"
        )

        cross_owner_update = account_b.request(
            "PATCH",
            params={"id": f"eq.{inserted_id}", "select": "id,title"},
            payload={"title": marker + " MODIFIED BY B"},
        )
        cross_owner_update.raise_for_status()
        assert cross_owner_update.json() == []

        unchanged = account_a.request("GET", params=row_filter)
        unchanged.raise_for_status()
        assert unchanged.json()[0]["title"] == marker

        # Both fixture accounts are deliberately non-Premium: Professional
        # workspace insertion must be rejected by the database policy itself.
        professional_insert = account_b.request(
            "POST",
            payload={
                "user_id": account_b.user_id,
                "workspace_id": "professional",
                "title": marker + " PROFESSIONAL",
                "description": "Must be denied to non-Premium test account",
                "status": "En cours",
            },
        )
        assert professional_insert.status_code in (401, 403), (
            "A non-Premium account must not insert into the Professional workspace; "
            f"received HTTP {professional_insert.status_code}"
        )
    finally:
        if inserted_id is not None:
            # No DELETE grant is intentionally provided. Keep the evidence row
            # archived rather than bypassing the application's no-hard-delete rule.
            archived = account_a.request(
                "PATCH",
                params={"id": f"eq.{inserted_id}"},
                payload={"archived_at": "now()", "updated_at": "now()"},
            )
            # PostgREST expects timestamp strings, not SQL expressions. If this
            # archival attempt fails, the synthetic row remains clearly marked.
            if archived.status_code >= 400:
                account_a.request(
                    "PATCH",
                    params={"id": f"eq.{inserted_id}"},
                    payload={"archived_at": "2026-11-14T00:00:00+00:00"},
                )

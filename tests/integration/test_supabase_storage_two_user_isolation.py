"""Opt-in live tests for per-user Supabase PDF Storage isolation.

Run only against a dedicated Supabase test project and two dedicated test users.
The tests use the public anon key and authenticated JWTs, never service_role.
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

BUCKET = "sowia-files"
PDF_FIXTURE = b"%PDF-1.4\n% SOW IA isolated storage test fixture\n%%EOF\n"


class StorageTestSession:
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
        }

    def object_request(self, method, path, **kwargs):
        return self.http.request(
            method,
            f"{self.url}/storage/v1/object/{BUCKET}/{path}",
            headers={**self.headers, **kwargs.pop("headers", {})},
            timeout=20,
            **kwargs,
        )

    def delete_object(self, path):
        return self.http.delete(
            f"{self.url}/storage/v1/object/{BUCKET}",
            headers={**self.headers, "Content-Type": "application/json"},
            json={"prefixes": [path]},
            timeout=20,
        )


def test_pdf_objects_are_private_to_their_authenticated_owner():
    """A owns its PDF; B cannot fetch, replace, or delete that object."""
    url = os.environ["SOWIA_TEST_SUPABASE_URL"]
    anon_key = os.environ["SOWIA_TEST_SUPABASE_ANON_KEY"]
    account_a = StorageTestSession(
        url, anon_key,
        os.environ["SOWIA_TEST_USER_A_EMAIL"],
        os.environ["SOWIA_TEST_USER_A_PASSWORD"],
    )
    account_b = StorageTestSession(
        url, anon_key,
        os.environ["SOWIA_TEST_USER_B_EMAIL"],
        os.environ["SOWIA_TEST_USER_B_PASSWORD"],
    )
    assert account_a.user_id != account_b.user_id

    object_name = "sowia-rls-" + uuid.uuid4().hex + ".pdf"
    path = f"{account_a.user_id}/personal/{object_name}"
    uploaded = False
    try:
        owner_upload = account_a.object_request(
            "POST",
            path,
            data=PDF_FIXTURE,
            headers={
                "Content-Type": "application/pdf",
                "x-upsert": "false",
            },
        )
        assert owner_upload.status_code in (200, 201), (
            "Account A could not upload its own PDF to the private bucket"
        )
        uploaded = True

        owner_download = account_a.object_request("GET", path)
        assert owner_download.status_code == 200
        assert owner_download.content == PDF_FIXTURE

        other_download = account_b.object_request("GET", path)
        assert not other_download.ok, (
            "Account B unexpectedly downloaded Account A's private PDF"
        )

        forged_upload = account_b.object_request(
            "POST",
            f"{account_a.user_id}/personal/sowia-forged-{uuid.uuid4().hex}.pdf",
            data=PDF_FIXTURE,
            headers={
                "Content-Type": "application/pdf",
                "x-upsert": "false",
            },
        )
        assert not forged_upload.ok, (
            "Account B unexpectedly uploaded an object under Account A's user folder"
        )

        # Storage APIs may report a policy error or a no-op for an unauthorized
        # delete. The decisive check is that A can still retrieve the exact bytes.
        account_b.delete_object(path)
        after_other_delete = account_a.object_request("GET", path)
        assert after_other_delete.status_code == 200
        assert after_other_delete.content == PDF_FIXTURE
    finally:
        if uploaded:
            cleanup = account_a.delete_object(path)
            assert cleanup.ok, "The owner could not remove the temporary test PDF"

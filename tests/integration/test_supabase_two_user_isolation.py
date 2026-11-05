"""Opt-in live RLS test using two dedicated Supabase test accounts.

Set SOWIA_TEST_SUPABASE_URL, SOWIA_TEST_SUPABASE_ANON_KEY,
SOWIA_TEST_USER_A_EMAIL, SOWIA_TEST_USER_A_PASSWORD,
SOWIA_TEST_USER_B_EMAIL and SOWIA_TEST_USER_B_PASSWORD.
Never use production accounts or credentials.
"""
import os
import uuid

import pytest
from supabase import create_client


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


def _signed_in_client(url, anon_key, email, password):
    client = create_client(url, anon_key)
    response = client.auth.sign_in_with_password(
        {"email": email, "password": password}
    )
    user = getattr(response, "user", None)
    assert user is not None and user.id, "Supabase test account did not authenticate"
    return client, user.id


def test_documents_are_isolated_between_two_authenticated_users():
    url = os.environ["SOWIA_TEST_SUPABASE_URL"]
    anon_key = os.environ["SOWIA_TEST_SUPABASE_ANON_KEY"]
    client_a, user_a_id = _signed_in_client(
        url, anon_key,
        os.environ["SOWIA_TEST_USER_A_EMAIL"],
        os.environ["SOWIA_TEST_USER_A_PASSWORD"],
    )
    client_b, user_b_id = _signed_in_client(
        url, anon_key,
        os.environ["SOWIA_TEST_USER_B_EMAIL"],
        os.environ["SOWIA_TEST_USER_B_PASSWORD"],
    )
    assert user_a_id != user_b_id, "The two test accounts must be different"

    marker = "sowia-rls-test-" + uuid.uuid4().hex
    document_id = None
    try:
        inserted = client_a.table("sowia_documents").insert({
            "user_id": user_a_id,
            "title": marker,
            "filename": marker + ".txt",
            "extracted_text": "Private RLS isolation test",
            "text_length": len("Private RLS isolation test"),
            "category": "Autres",
            "folder": "Général",
        }).execute()
        assert inserted.data, "Account A could not create its isolated test row"
        document_id = inserted.data[0]["id"]

        visible_to_a = (
            client_a.table("sowia_documents")
            .select("id, title")
            .eq("id", document_id)
            .execute()
            .data
        )
        visible_to_b = (
            client_b.table("sowia_documents")
            .select("id, title")
            .eq("id", document_id)
            .execute()
            .data
        )
        assert any(row["id"] == document_id for row in visible_to_a)
        assert not any(row["id"] == document_id for row in visible_to_b)

        # A user must not be able to create a row owned by another account.
        with pytest.raises(Exception):
            client_b.table("sowia_documents").insert({
                "user_id": user_a_id,
                "title": marker + "-forged",
                "filename": marker + "-forged.txt",
                "extracted_text": "Must be rejected by RLS",
                "text_length": len("Must be rejected by RLS"),
                "category": "Autres",
                "folder": "Général",
            }).execute()

        # Even if B knows the row id, RLS must prevent mutation or deletion.
        client_b.table("sowia_documents").update(
            {"title": marker + "-tampered"}
        ).eq("id", document_id).execute()
        client_b.table("sowia_documents").delete().eq(
            "id", document_id
        ).execute()

        still_owned_by_a = (
            client_a.table("sowia_documents")
            .select("id, title")
            .eq("id", document_id)
            .execute()
            .data
        )
        assert any(
            row["id"] == document_id and row["title"] == marker
            for row in still_owned_by_a
        )
    finally:
        if document_id is not None:
            client_a.table("sowia_documents").delete().eq(
                "id", document_id
            ).eq("user_id", user_a_id).execute()

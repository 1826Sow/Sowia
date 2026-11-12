"""Live RLS integration for all Professional modules.

Runs only on a dedicated disposable Supabase project. service_role is restricted
to temporary fixtures and cleanup; every authorization assertion uses a signed
user JWT issued by Supabase Auth.
"""
from __future__ import annotations

import os
import uuid
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
_MISSING = [key for key in _REQUIRED if not os.getenv(key)]
if not _MISSING and os.environ["SOWIA_TEST_PROJECT_CONFIRMATION"] != _CONFIRMATION:
    raise RuntimeError("Refusing live tests: dedicated disposable Supabase project confirmation is invalid")
pytestmark = pytest.mark.skipif(bool(_MISSING), reason="Dedicated Supabase test-project credentials are not configured")

PROFESSIONAL_TABLES = (
    "sowia_growth_leads",
    "sowia_relationship_events",
    "sowia_business_opportunities",
    "sowia_business_club_profiles",
    "sowia_business_club_requests",
    "sowia_business_club_meetings",
    "sowia_business_club_notifications",
    "sowia_night_exchange_apps",
    "sowia_night_exchange_events",
)


def _url():
    value = os.environ["SOWIA_TEST_SUPABASE_URL"].strip()
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https" or not parsed.hostname
        or not parsed.hostname.endswith(".supabase.co")
        or parsed.username or parsed.password or parsed.port
        or parsed.query or parsed.fragment or parsed.path not in ("", "/")
    ):
        raise ValueError("Refusing live tests: expected a plain hosted HTTPS Supabase project URL")
    return value.rstrip("/")


class Api:
    def __init__(self, key: str, bearer: str | None = None):
        self.base = _url()
        self.session = requests.Session()
        self.headers = {"apikey": key, "Content-Type": "application/json"}
        if bearer:
            self.headers["Authorization"] = f"Bearer {bearer}"

    def call(self, method: str, path: str, *, params=None, body=None, prefer=None):
        headers = dict(self.headers)
        if prefer:
            headers["Prefer"] = prefer
        return self.session.request(
            method, f"{self.base}{path}", headers=headers,
            params=params, json=body, timeout=20, allow_redirects=False,
        )

    def rows(self, table: str, *, params=None):
        response = self.call("GET", f"/rest/v1/{table}", params=params)
        response.raise_for_status()
        return response.json()

    def insert(self, table: str, payload: dict, *, select="*", required=True):
        response = self.call(
            "POST", f"/rest/v1/{table}", params={"select": select},
            body=payload, prefer="return=representation",
        )
        if required:
            response.raise_for_status()
        return response

    def delete(self, table: str, row_id):
        response = self.call("DELETE", f"/rest/v1/{table}", params={"id": f"eq.{row_id}"})
        response.raise_for_status()
        return response


def _login(api_key, email, password):
    bootstrap = Api(api_key)
    response = bootstrap.call(
        "POST", "/auth/v1/token", params={"grant_type": "password"},
        body={"email": email, "password": password},
    )
    response.raise_for_status()
    payload = response.json()
    return Api(api_key, payload["access_token"]), payload["user"]["id"]


def _admin_user(admin: Api, email: str, password: str):
    response = admin.call(
        "POST", "/auth/v1/admin/users",
        body={
            "email": email, "password": password, "email_confirm": True,
            "app_metadata": {"role": "admin", "sowia_admin": "true"},
        },
    )
    response.raise_for_status()
    return response.json()["id"]


def _entitlement(admin: Api, user_id: str, active: bool):
    payload = {
        "user_id": user_id, "status": "active" if active else "inactive",
        "provider": "paypal", "paypal_order_id": f"rls-test-{user_id}",
        "amount": 1, "currency": "EUR",
    }
    response = admin.call(
        "POST", "/rest/v1/sowia_entitlements",
        params={"on_conflict": "user_id"},
        body=payload, prefer="resolution=merge-duplicates,return=minimal",
    )
    response.raise_for_status()


def _expect_hidden(client: Api, table: str, row_id):
    rows = client.rows(table, params={"id": f"eq.{row_id}", "select": "id"})
    assert not rows, f"{table} row {row_id} leaked to a user without Professional access"


def _expect_denied(response, operation: str):
    assert response.status_code in (401, 403), (
        f"{operation} should be rejected by grants/RLS; received HTTP {response.status_code}: "
        f"{response.text[:300]}"
    )


def test_professional_module_rls_real_accounts_and_admin_exception():
    """Exercise Personal/Professional, Premium expiry, participants and admin limits."""
    anon = os.environ["SOWIA_TEST_SUPABASE_ANON_KEY"]
    admin = Api(os.environ["SOWIA_TEST_SUPABASE_SERVICE_ROLE_KEY"],
                os.environ["SOWIA_TEST_SUPABASE_SERVICE_ROLE_KEY"])
    a, user_a = _login(anon, os.environ["SOWIA_TEST_USER_A_EMAIL"], os.environ["SOWIA_TEST_USER_A_PASSWORD"])
    b, user_b = _login(anon, os.environ["SOWIA_TEST_USER_B_EMAIL"], os.environ["SOWIA_TEST_USER_B_PASSWORD"])
    assert user_a != user_b

    # Fail with a precise prerequisite message rather than silently omitting tables.
    for table in PROFESSIONAL_TABLES:
        probe = admin.call("GET", f"/rest/v1/{table}", params={"select": "*", "limit": 0})
        if not probe.ok:
            pytest.fail(
                f"Missing/unavailable table public.{table} (HTTP {probe.status_code}). "
                "Apply the seven module DDL scripts and migrations in docs/SUPABASE_INSTALLATION_ORDER.md "
                "to this disposable test project before running live RLS tests."
            )

    # C is a real, short-lived Auth user with signed app_metadata, not user_metadata.
    suffix = uuid.uuid4().hex[:12]
    c_email = f"sowia-rls-admin-{suffix}@example.invalid"
    c_password = f"Rls-Test-{uuid.uuid4().hex}-Aa9!"
    user_c = None
    fixture_ids: dict[str, list] = {table: [] for table in PROFESSIONAL_TABLES}
    entitlement_snapshots = {}
    subscription_snapshots = {}
    try:
        # Preserve and restore A/B entitlements even though this is a disposable project.
        for uid in (user_a, user_b):
            old = admin.rows("sowia_entitlements", params={"user_id": f"eq.{uid}", "select": "*"})
            entitlement_snapshots[uid] = old[0] if old else None
            subscription_snapshots[uid] = admin.rows(
                "sowia_subscriptions", params={"user_id": f"eq.{uid}", "select": "id,status"}
            )
            # Remove any pre-existing recurring Premium grant during the test;
            # restore its exact status in finally.
            for subscription in subscription_snapshots[uid]:
                if subscription["status"] == "active":
                    changed = admin.call(
                        "PATCH", "/rest/v1/sowia_subscriptions",
                        params={"id": f"eq.{subscription['id']}"},
                        body={"status": "inactive"},
                    )
                    changed.raise_for_status()
        user_c = _admin_user(admin, c_email, c_password)
        c, logged_c = _login(anon, c_email, c_password)
        assert logged_c == user_c

        _entitlement(admin, user_a, True)
        _entitlement(admin, user_b, True)
        # C has admin claims but deliberately has no Premium entitlement.
        c_ent = admin.call("DELETE", "/rest/v1/sowia_entitlements", params={"user_id": f"eq.{user_c}"})
        c_ent.raise_for_status()

        marker = uuid.uuid4().hex

        # CRM: Personal rows stay available without Premium; Professional rows
        # require Premium and remain owner-isolated.
        lead_a = admin.insert("sowia_growth_leads", {
            "user_id": user_a, "workspace_id": "professional",
            "organization": f"RLS Org {marker}", "country": "FR",
        }).json()[0]
        fixture_ids["sowia_growth_leads"].append(lead_a["id"])
        lead_personal_c = admin.insert("sowia_growth_leads", {
            "user_id": user_c, "workspace_id": "personal",
            "organization": f"Personal {marker}", "country": "FR",
        }).json()[0]
        fixture_ids["sowia_growth_leads"].append(lead_personal_c["id"])

        event_a = admin.insert("sowia_relationship_events", {
            "user_id": user_a, "workspace_id": "professional", "lead_id": lead_a["id"],
            "title": f"RLS follow-up {marker}", "event_type": "Autre", "due_date": "2030-01-01",
        }).json()[0]
        fixture_ids["sowia_relationship_events"].append(event_a["id"])
        opportunity_a = admin.insert("sowia_business_opportunities", {
            "user_id": user_a, "workspace_id": "professional",
            "niche": "test", "offer": f"RLS offer {marker}",
        }).json()[0]
        fixture_ids["sowia_business_opportunities"].append(opportunity_a["id"])

        assert a.rows("sowia_growth_leads", params={"id": f"eq.{lead_a['id']}", "select": "id"})
        _expect_hidden(b, "sowia_growth_leads", lead_a["id"])
        assert c.rows("sowia_growth_leads", params={"id": f"eq.{lead_personal_c['id']}", "select": "id"})
        _expect_hidden(c, "sowia_growth_leads", lead_a["id"])
        _expect_hidden(b, "sowia_relationship_events", event_a["id"])
        _expect_hidden(b, "sowia_business_opportunities", opportunity_a["id"])

        # Revoke A's Premium: all Professional CRM rows become invisible, while
        # Personal data remains visible to its owner.
        _entitlement(admin, user_a, False)
        _expect_hidden(a, "sowia_growth_leads", lead_a["id"])
        _expect_hidden(a, "sowia_relationship_events", event_a["id"])
        _expect_hidden(a, "sowia_business_opportunities", opportunity_a["id"])
        assert c.rows("sowia_growth_leads", params={"id": f"eq.{lead_personal_c['id']}", "select": "id"})
        _entitlement(admin, user_a, True)

        # Business Club: A owns a published profile; B sends a request; C is
        # neither participant and must not read the private request/meeting/inbox.
        profile = admin.insert("sowia_business_club_profiles", {
            "user_id": user_a, "workspace_id": "professional",
            "company_name": f"Company {marker}", "country": "FR", "sector": "test",
            "is_published": True,
        }).json()[0]
        fixture_ids["sowia_business_club_profiles"].append(profile["id"])
        request = admin.insert("sowia_business_club_requests", {
            "profile_id": profile["id"], "sender_user_id": user_b,
            "recipient_user_id": user_a, "message": f"Hello {marker}", "status": "En attente",
        }).json()[0]
        fixture_ids["sowia_business_club_requests"].append(request["id"])
        accepted = a.call(
            "PATCH", "/rest/v1/sowia_business_club_requests",
            params={"id": f"eq.{request['id']}", "status": "eq.En attente"},
            body={"status": "Acceptée"}, prefer="return=representation",
        )
        accepted.raise_for_status()
        assert admin.rows("sowia_business_club_requests", params={
            "id": f"eq.{request['id']}", "select": "status"
        })[0]["status"] == "Acceptée"
        meeting = admin.insert("sowia_business_club_meetings", {
            "request_id": request["id"], "organizer_user_id": user_b,
            "sender_user_id": user_b, "recipient_user_id": user_a,
            "invitee_user_id": user_a, "starts_at": "2030-01-01T12:00:00Z",
            "timezone": "Europe/Paris", "duration_minutes": 30, "status": "Proposée",
        }).json()[0]
        fixture_ids["sowia_business_club_meetings"].append(meeting["id"])
        confirmed = a.call(
            "PATCH", "/rest/v1/sowia_business_club_meetings",
            params={"id": f"eq.{meeting['id']}", "status": "eq.Proposée"},
            body={"status": "Confirmée"}, prefer="return=representation",
        )
        confirmed.raise_for_status()
        assert admin.rows("sowia_business_club_meetings", params={
            "id": f"eq.{meeting['id']}", "select": "status"
        })[0]["status"] == "Confirmée"
        # The meeting trigger creates a private invitee notification.
        meeting_inbox = admin.rows("sowia_business_club_notifications", params={
            "user_id": f"eq.{user_a}", "entity_id": f"eq.{meeting['id']}",
            "entity_type": "eq.meeting", "event_type": "eq.meeting_proposed", "select": "id",
        })
        fixture_ids["sowia_business_club_notifications"].extend(
            row["id"] for row in meeting_inbox
        )
        # The request trigger creates A's inbox notification. Add a distinct
        # B-owned notification so Premium expiry can be tested on the owner.
        inbox_a = admin.rows("sowia_business_club_notifications", params={
            "user_id": f"eq.{user_a}", "entity_id": f"eq.{request['id']}",
            "event_type": "eq.request_received", "select": "id",
        })
        assert inbox_a, "Business Club request trigger did not create the recipient notification"
        fixture_ids["sowia_business_club_notifications"].extend(row["id"] for row in inbox_a)
        inbox_b_rows = admin.rows("sowia_business_club_notifications", params={
            "user_id": f"eq.{user_b}", "entity_id": f"eq.{request['id']}",
            "event_type": "eq.request_accepted", "select": "id",
        })
        assert inbox_b_rows, "Business Club acceptance trigger did not notify the sender"
        fixture_ids["sowia_business_club_notifications"].extend(
            row["id"] for row in inbox_b_rows
        )
        meeting_inbox_b = admin.rows("sowia_business_club_notifications", params={
            "user_id": f"eq.{user_b}", "entity_id": f"eq.{meeting['id']}",
            "entity_type": "eq.meeting", "event_type": "eq.meeting_confirmed", "select": "id",
        })
        assert meeting_inbox_b, "Business Club meeting confirmation trigger did not notify the organizer"
        fixture_ids["sowia_business_club_notifications"].extend(
            row["id"] for row in meeting_inbox_b
        )
        inbox_b = inbox_b_rows[0]

        # A and B are participants; C is not. Profile is public only while published.
        assert b.rows("sowia_business_club_profiles", params={"id": f"eq.{profile['id']}", "select": "id"})
        assert a.rows("sowia_business_club_requests", params={"id": f"eq.{request['id']}", "select": "id"})
        assert b.rows("sowia_business_club_requests", params={"id": f"eq.{request['id']}", "select": "id"})
        _expect_hidden(c, "sowia_business_club_requests", request["id"])
        assert a.rows("sowia_business_club_meetings", params={"id": f"eq.{meeting['id']}", "select": "id"})
        assert b.rows("sowia_business_club_meetings", params={"id": f"eq.{meeting['id']}", "select": "id"})
        _expect_hidden(c, "sowia_business_club_meetings", meeting["id"])
        assert b.rows("sowia_business_club_notifications", params={"id": f"eq.{inbox_b['id']}", "select": "id"})
        _expect_hidden(c, "sowia_business_club_notifications", inbox_a[0]["id"])

        # No Premium blocks Business Club even when the profile is published,
        # and revoking entitlement hides the member's own private inbox.
        _entitlement(admin, user_b, False)
        _expect_hidden(b, "sowia_business_club_profiles", profile["id"])
        _expect_hidden(b, "sowia_business_club_requests", request["id"])
        _expect_hidden(b, "sowia_business_club_notifications", inbox_b["id"])
        _entitlement(admin, user_b, True)

        # NIGHT EXCHANGE: admin C can inspect pending queue without Premium;
        # direct writes are denied by restrictive WITH CHECK, guarded RPC works.
        app = admin.insert("sowia_night_exchange_apps", {
            "user_id": user_a, "workspace_id": "professional",
            "app_name": f"Test app {marker}", "country": "FR", "timezone": "Europe/Paris",
            "categories": ["integration"], "services_offered": "test",
            "services_wanted": "test", "status": "pending",
        }).json()[0]
        fixture_ids["sowia_night_exchange_apps"].append(app["id"])
        queue = c.rows("sowia_night_exchange_apps", params={"id": f"eq.{app['id']}", "select": "id,status"})
        assert queue and queue[0]["status"] == "pending"
        _expect_hidden(b, "sowia_night_exchange_apps", app["id"])

        direct_admin_update = c.call(
            "PATCH", "/rest/v1/sowia_night_exchange_apps",
            params={"id": f"eq.{app['id']}"},
            body={"status": "approved"},
            prefer="return=representation",
        )
        _expect_denied(direct_admin_update, "NIGHT EXCHANGE direct admin UPDATE")
        rpc = c.call(
            "POST", "/rest/v1/rpc/sowia_admin_review_nex_app",
            body={"p_app_id": app["id"], "p_status": "approved", "p_moderation_note": "RLS test approval"},
        )
        rpc.raise_for_status()
        assert c.rows("sowia_night_exchange_apps", params={"id": f"eq.{app['id']}", "select": "id,status"})[0]["status"] == "approved"
        assert b.rows("sowia_night_exchange_apps", params={"id": f"eq.{app['id']}", "select": "id,status"})[0]["status"] == "approved"

        # NIGHT EXCHANGE event ledger is Premium-only, owner-readable, append-only,
        # and clients cannot forge payment confirmation.
        event = admin.insert("sowia_night_exchange_events", {
            "user_id": user_a, "workspace_id": "professional", "app_id": app["id"],
            "event_type": "match_viewed", "event_payload": {"test": marker},
        }).json()[0]
        fixture_ids["sowia_night_exchange_events"].append(event["id"])
        assert a.rows("sowia_night_exchange_events", params={"id": f"eq.{event['id']}", "select": "id"})
        _expect_hidden(b, "sowia_night_exchange_events", event["id"])
        payment_forge = a.insert("sowia_night_exchange_events", {
            "user_id": user_a, "workspace_id": "professional", "app_id": app["id"],
            "event_type": "payment_confirmed", "event_payload": {"test": marker},
        }, required=False)
        _expect_denied(payment_forge, "client NIGHT EXCHANGE payment_confirmed INSERT")
        update_event = a.call(
            "PATCH", "/rest/v1/sowia_night_exchange_events",
            params={"id": f"eq.{event['id']}"}, body={"event_payload": {"tampered": True}},
        )
        _expect_denied(update_event, "NIGHT EXCHANGE event UPDATE")
        delete_event = a.call(
            "DELETE", "/rest/v1/sowia_night_exchange_events",
            params={"id": f"eq.{event['id']}"},
        )
        _expect_denied(delete_event, "NIGHT EXCHANGE event DELETE")

        # C admin exception must not grant event history or other Professional
        # tables without entitlement.
        _expect_hidden(c, "sowia_night_exchange_events", event["id"])
        _expect_hidden(c, "sowia_growth_leads", lead_a["id"])

        # No-Premium account C cannot create a Professional CRM record either.
        denied_insert = c.insert("sowia_growth_leads", {
            "user_id": user_c, "workspace_id": "professional",
            "organization": f"Forbidden {marker}", "country": "FR",
        }, required=False)
        _expect_denied(denied_insert, "Professional CRM INSERT without Premium")
    finally:
        # Re-discover trigger-created notifications so cleanup still works if
        # an earlier assertion failed before their IDs were recorded.
        for source_table, entity_type in (
            ("sowia_business_club_requests", "request"),
            ("sowia_business_club_meetings", "meeting"),
        ):
            for entity_id in fixture_ids[source_table]:
                notices = admin.rows("sowia_business_club_notifications", params={
                    "entity_id": f"eq.{entity_id}", "entity_type": f"eq.{entity_type}",
                    "select": "id",
                })
                fixture_ids["sowia_business_club_notifications"].extend(
                    row["id"] for row in notices
                )
        # Delete fixtures in dependency order. Cleanup uses only the disposable
        # project's service role and must not hide an earlier assertion failure.
        for table in (
            "sowia_night_exchange_events", "sowia_business_club_notifications",
            "sowia_business_club_meetings", "sowia_business_club_requests",
            "sowia_business_club_profiles", "sowia_relationship_events",
            "sowia_business_opportunities", "sowia_growth_leads",
            "sowia_night_exchange_apps",
        ):
            for row_id in fixture_ids[table]:
                cleanup = admin.call("DELETE", f"/rest/v1/{table}", params={"id": f"eq.{row_id}"})
                if cleanup.status_code not in (200, 204):
                    pytest.fail(f"Could not clean test fixture {table}/{row_id}: HTTP {cleanup.status_code}")
        for uid, old in entitlement_snapshots.items():
            if old is None:
                response = admin.call("DELETE", "/rest/v1/sowia_entitlements", params={"user_id": f"eq.{uid}"})
            else:
                response = admin.call(
                    "POST", "/rest/v1/sowia_entitlements", params={"on_conflict": "user_id"},
                    body=old, prefer="resolution=merge-duplicates,return=minimal",
                )
            if response.status_code not in (200, 201, 204):
                pytest.fail(f"Could not restore test entitlement for {uid}: HTTP {response.status_code}")
        for uid, subscriptions in subscription_snapshots.items():
            for subscription in subscriptions:
                restored = admin.call(
                    "PATCH", "/rest/v1/sowia_subscriptions",
                    params={"id": f"eq.{subscription['id']}"},
                    body={"status": subscription["status"]},
                )
                if restored.status_code not in (200, 204):
                    pytest.fail(f"Could not restore subscription status for {uid}: HTTP {restored.status_code}")
        if user_c:
            deleted = admin.call("DELETE", f"/auth/v1/admin/users/{user_c}")
            if deleted.status_code not in (200, 204):
                pytest.fail(f"Could not delete temporary admin test user: HTTP {deleted.status_code}")

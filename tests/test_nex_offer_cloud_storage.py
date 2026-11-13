"""Focused unit tests for the NIGHT EXCHANGE Supabase client helpers.

These tests mock Supabase's fluent API; database authorization is covered by SQL tests.
"""
import unittest
from types import SimpleNamespace

import cloud_storage


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, data=None):
        self.data = data if data is not None else []
        self.filters = []
        self.selected = None
        self.ordered = None
        self.row_limit = None

    def select(self, value):
        self.selected = value
        return self

    def eq(self, key, value):
        self.filters.append((key, value))
        return self

    def order(self, key, desc=False):
        self.ordered = (key, desc)
        return self

    def limit(self, value):
        self.row_limit = value
        return self

    def execute(self):
        return FakeResponse(self.data)


class FakeClient:
    def __init__(self, rpc_data=None, table_data=None):
        self.rpc_calls = []
        self.rpc_data = rpc_data
        self.query = FakeQuery(table_data)

    def rpc(self, name, params):
        self.rpc_calls.append((name, params))
        return SimpleNamespace(execute=lambda: FakeResponse(self.rpc_data))

    def table(self, name):
        self.table_name = name
        return self.query


class NightExchangeOfferHelperTests(unittest.TestCase):
    def setUp(self):
        self.user = SimpleNamespace(id="user-123", app_metadata={"role": "admin"})

    def test_create_offer_trims_summary_and_uses_guarded_rpc(self):
        client = FakeClient(rpc_data="offer-456", table_data=[{"id": "offer-456"}])
        result = cloud_storage.create_night_exchange_offer(
            client, self.user, "sender-app", "recipient-app", "  Collaboration proposal  "
        )
        self.assertEqual(result, "offer-456")
        self.assertEqual(client.rpc_calls, [(
            "sowia_nex_create_offer",
            {
                "p_sender_app_id": "sender-app",
                "p_recipient_app_id": "recipient-app",
                "p_offer_summary": "Collaboration proposal",
            },
        )])
        self.assertEqual(client.table_name, "sowia_night_exchange_offers")
        self.assertIn(("sender_user_id", "user-123"), client.query.filters)
        self.assertIn(("workspace_id", "professional"), client.query.filters)

    def test_create_offer_fails_closed_when_rpc_returns_no_identifier(self):
        client = FakeClient(rpc_data=None)
        with self.assertRaisesRegex(RuntimeError, "aucun identifiant"):
            cloud_storage.create_night_exchange_offer(
                client, self.user, "sender-app", "recipient-app",
                "A sufficiently long collaboration proposal"
            )
        self.assertEqual(len(client.rpc_calls), 1)

    def test_create_offer_fails_when_new_row_is_not_visible_in_sender_outbox(self):
        client = FakeClient(rpc_data="offer-456", table_data=[])
        with self.assertRaisesRegex(RuntimeError, "pas visible dans la boîte d'envoi"):
            cloud_storage.create_night_exchange_offer(
                client, self.user, "sender-app", "recipient-app",
                "A sufficiently long collaboration proposal"
            )

    def test_create_offer_rejects_short_summary_before_rpc(self):
        client = FakeClient()
        with self.assertRaises(ValueError):
            cloud_storage.create_night_exchange_offer(
                client, self.user, "sender-app", "recipient-app", "short"
            )
        self.assertEqual(client.rpc_calls, [])

    def test_offer_response_only_accepts_supported_decisions(self):
        client = FakeClient()
        with self.assertRaises(ValueError):
            cloud_storage.respond_night_exchange_offer(
                client, self.user, "offer-456", "cancelled"
            )
        self.assertEqual(client.rpc_calls, [])

    def test_offer_response_calls_recipient_guarded_rpc(self):
        client = FakeClient(rpc_data=None)
        cloud_storage.respond_night_exchange_offer(
            client, self.user, "offer-456", "accepted"
        )
        self.assertEqual(client.rpc_calls, [(
            "sowia_nex_respond_offer",
            {"p_offer_id": "offer-456", "p_decision": "accepted"},
        )])

    def test_offer_listing_is_user_and_workspace_scoped_and_caps_limit(self):
        client = FakeClient(table_data=[{"id": "offer-1"}])
        rows = cloud_storage.list_night_exchange_offers(
            client, self.user, workspace_id="professional", direction="inbox", limit=999
        )
        self.assertEqual(rows, [{"id": "offer-1"}])
        self.assertEqual(client.table_name, "sowia_night_exchange_offers")
        self.assertIn(("recipient_user_id", "user-123"), client.query.filters)
        self.assertIn(("workspace_id", "professional"), client.query.filters)
        self.assertEqual(client.query.row_limit, 200)

    def test_offer_listing_rejects_invalid_direction(self):
        client = FakeClient()
        with self.assertRaises(ValueError):
            cloud_storage.list_night_exchange_offers(
                client, self.user, direction="all"
            )
        self.assertIsNone(getattr(client, "table_name", None))

    def test_approved_directory_is_scoped_to_professional_workspace(self):
        client = FakeClient(table_data=[{"id": "professional-app"}])
        rows = cloud_storage.list_approved_night_exchange_apps(client, self.user)
        self.assertEqual(rows, [{"id": "professional-app"}])
        self.assertEqual(client.table_name, "sowia_night_exchange_apps")
        self.assertIn(("status", "approved"), client.query.filters)
        self.assertIn(("workspace_id", "professional"), client.query.filters)

    def test_admin_queue_requires_admin_metadata(self):
        client = FakeClient(rpc_data=[])
        ordinary_user = SimpleNamespace(id="user-123", app_metadata={"role": "member"})
        with self.assertRaises(PermissionError):
            cloud_storage.list_night_exchange_integrations_for_admin(client, ordinary_user)
        self.assertEqual(client.rpc_calls, [])

    def test_admin_queue_handles_empty_result_and_caps_limit(self):
        client = FakeClient(rpc_data=None)
        rows = cloud_storage.list_night_exchange_integrations_for_admin(
            client, self.user, limit=500
        )
        self.assertEqual(rows, [])
        self.assertEqual(client.rpc_calls, [("sowia_admin_list_nex_integrations", {})])

    def test_admin_review_rejects_invalid_decision_before_rpc(self):
        client = FakeClient()
        with self.assertRaises(ValueError):
            cloud_storage.admin_review_night_exchange_integration(
                client, self.user, "offer-456", "accepted", ""
            )
        self.assertEqual(client.rpc_calls, [])

    def test_admin_review_uses_signed_admin_rpc(self):
        client = FakeClient()
        cloud_storage.admin_review_night_exchange_integration(
            client, self.user, "offer-456", "approved", "Reviewed"
        )
        self.assertEqual(client.rpc_calls, [(
            "sowia_admin_review_nex_integration",
            {
                "p_offer_id": "offer-456",
                "p_decision": "approved",
                "p_review_note": "Reviewed",
            },
        )])

    def test_rejected_integration_is_counted_in_activity_report(self):
        from sowia_night_exchange import build_morning_report

        report = build_morning_report([
            {"event_type": "integration_rejected", "event_payload": {"offer_id": "offer-456"}},
            {"event_type": "integration_approved", "event_payload": {"offer_id": "offer-789"}},
        ])

        self.assertEqual(report["counts"]["integration_rejected"], 1)
        self.assertEqual(report["counts"]["integration_approved"], 1)
        self.assertEqual(report["recognized_events"], 2)
        self.assertEqual(report["confirmed_spend"], 0)


if __name__ == "__main__":
    unittest.main()

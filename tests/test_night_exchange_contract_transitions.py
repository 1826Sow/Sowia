"""Static security-contract tests for NIGHT EXCHANGE contract transitions.

These checks are not a substitute for PostgreSQL concurrency and RLS integration tests.
"""
from pathlib import Path
import unittest


MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "supabase"
    / "migrations"
    / "20261121000200_night_exchange_contract_transitions.sql"
)


class NightExchangeContractTransitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sql = MIGRATION.read_text(encoding="utf-8").lower()

    def test_rpc_is_security_definer_with_empty_search_path(self):
        self.assertIn("security definer", self.sql)
        self.assertIn("set search_path = ''", self.sql)
        self.assertIn("auth.uid()", self.sql)

    def test_rpc_checks_participant_and_locks_deal_row(self):
        self.assertIn("for update", self.sql)
        self.assertIn("not a deal participant", self.sql)
        self.assertIn("v_actor <> v_deal.created_by", self.sql)

    def test_only_allowed_state_transitions_are_encoded(self):
        for transition in (
            "p_target_status = 'accepted'",
            "p_target_status in ('in_progress', 'cancelled')",
            "p_target_status = 'completed'",
            "p_target_status = 'disputed'",
        ):
            self.assertIn(transition, self.sql)
        self.assertIn("transition not permitted", self.sql)

    def test_status_update_and_audit_insert_are_in_same_function(self):
        self.assertIn("update public.sowia_nex_deals", self.sql)
        self.assertIn("insert into public.sowia_nex_deal_events", self.sql)
        self.assertIn("'status_changed'", self.sql)

    def test_idempotency_is_unique_per_actor_and_replay_safe(self):
        self.assertIn(
            "on public.sowia_nex_deal_events (actor_user_id, idempotency_key)",
            self.sql,
        )
        self.assertIn("retry with the same key returns the original event", self.sql)
        self.assertIn("idempotency key already used for another deal", self.sql)
        self.assertIn("idempotency key reused with a different request", self.sql)
        self.assertIn("(v_existing_payload ->> 'to') is distinct from p_target_status", self.sql)
        self.assertIn("p_target_status is null", self.sql)

    def test_clients_cannot_use_rpc_for_financial_confirmation(self):
        self.assertNotIn("'payment_confirmed'", self.sql)
        self.assertNotIn("'refund_confirmed'", self.sql)
        self.assertNotIn("'commission_recognized'", self.sql)

    def test_execute_is_revoked_then_granted_only_to_authenticated(self):
        self.assertIn("from public, anon, authenticated", self.sql)
        self.assertIn("to authenticated", self.sql)
        self.assertNotIn("to anon", self.sql)

    def test_migration_is_additive(self):
        self.assertIn("add column if not exists", self.sql)
        self.assertNotIn("drop table", self.sql)
        self.assertNotIn("truncate", self.sql)


if __name__ == "__main__":
    unittest.main()

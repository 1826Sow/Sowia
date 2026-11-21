"""Static security-contract tests for automatic proposal audit events."""
from pathlib import Path
import unittest


MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "supabase"
    / "migrations"
    / "20261121000300_night_exchange_proposal_audit.sql"
)


class NightExchangeProposalAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sql = MIGRATION.read_text(encoding="utf-8").lower()

    def test_proposal_creation_automatically_appends_audit_event(self):
        self.assertIn("after insert on public.sowia_nex_deals", self.sql)
        self.assertIn("insert into public.sowia_nex_deal_events", self.sql)
        self.assertIn("'proposal_created'", self.sql)
        self.assertIn("new.created_by", self.sql)
        self.assertIn("new.id", self.sql)

    def test_trigger_function_uses_restricted_definer_context(self):
        self.assertIn("security definer", self.sql)
        self.assertIn("set search_path = ''", self.sql)
        self.assertIn("from public, anon, authenticated", self.sql)

    def test_proposal_event_does_not_consume_transition_idempotency_key(self):
        self.assertNotIn("idempotency_key", self.sql)

    def test_trigger_is_additive(self):
        self.assertIn("create trigger sowia_nex_deals_audit_proposal", self.sql)
        self.assertNotIn("drop table", self.sql)
        self.assertNotIn("truncate", self.sql)


if __name__ == "__main__":
    unittest.main()

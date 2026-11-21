"""Static security contract tests for the NIGHT EXCHANGE SQL migration.

These tests do not replace PostgreSQL/RLS integration tests. They guard critical
migration invariants in the repository CI without connecting to production.
"""
from pathlib import Path
import re
import unittest


MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "supabase"
    / "migrations"
    / "20261121000100_night_exchange_commercial_ledger.sql"
)


class NightExchangeLedgerMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sql = MIGRATION.read_text(encoding="utf-8").lower()

    def test_both_tables_enable_row_level_security(self):
        self.assertRegex(
            self.sql,
            r"alter table public\.sowia_nex_deals enable row level security",
        )
        self.assertRegex(
            self.sql,
            r"alter table public\.sowia_nex_deal_events enable row level security",
        )

    def test_deal_reads_are_limited_to_participants(self):
        self.assertIn('"nex_deals_participant_read"', self.sql)
        self.assertIn("created_by = (select auth.uid())", self.sql)
        self.assertIn("counterparty_user_id = (select auth.uid())", self.sql)

    def test_clients_cannot_create_authoritative_financial_events(self):
        policy = re.search(
            r'create policy "nex_deal_events_client_non_authoritative_insert".*?;',
            self.sql,
            re.S,
        )
        self.assertIsNotNone(policy)
        self.assertIn("'meeting_scheduled'", policy.group(0))
        self.assertIn("'note_added'", policy.group(0))
        self.assertIn("'delivery_evidence_submitted'", policy.group(0))
        self.assertNotIn("'payment_confirmed'", policy.group(0))
        self.assertNotIn("'commission_recognized'", policy.group(0))

    def test_event_history_rejects_updates_and_deletes(self):
        self.assertIn("sowia_nex_reject_event_mutation", self.sql)
        self.assertRegex(
            self.sql,
            r"before update or delete on public\.sowia_nex_deal_events",
        )
        self.assertIn("raise exception 'night exchange events are append-only'", self.sql)

    def test_commission_is_a_forecast_not_recognized_revenue(self):
        self.assertRegex(
            self.sql,
            r"planned_commission numeric\(18,2\).*?generated always as",
            re.S,
        )
        self.assertIn("planned_commission is not recognized revenue", self.sql)

    def test_no_public_or_anonymous_table_access(self):
        self.assertIn("revoke all on public.sowia_nex_deals from anon, authenticated", self.sql)
        self.assertIn("revoke all on public.sowia_nex_deal_events from anon, authenticated", self.sql)
        self.assertNotRegex(self.sql, r"grant .* to anon\b")

    def test_migration_is_additive_and_does_not_drop_existing_objects(self):
        self.assertIn("create table if not exists public.sowia_nex_deals", self.sql)
        self.assertIn("create table if not exists public.sowia_nex_deal_events", self.sql)
        self.assertNotRegex(self.sql, r"\bdrop table\b")
        self.assertNotRegex(self.sql, r"\btruncate\b")


if __name__ == "__main__":
    unittest.main()

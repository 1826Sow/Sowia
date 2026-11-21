"""Static security-contract tests for trusted NIGHT EXCHANGE deal creation."""
from pathlib import Path
import unittest


MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "supabase"
    / "migrations"
    / "20261121000400_night_exchange_deal_creation.sql"
)


class NightExchangeDealCreationMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sql = MIGRATION.read_text(encoding="utf-8").lower()

    def test_creation_is_server_only_and_authenticated(self):
        self.assertIn("security definer", self.sql)
        self.assertIn("set search_path = ''", self.sql)
        self.assertIn("auth.uid()", self.sql)
        self.assertIn("public.sowia_has_professional_access()", self.sql)
        self.assertIn("active premium access required", self.sql)
        self.assertIn("from public, anon, authenticated", self.sql)
        self.assertIn("to authenticated", self.sql)

    def test_direct_client_insert_is_revoked(self):
        self.assertIn("revoke insert on public.sowia_nex_deals from authenticated", self.sql)
        self.assertIn("grant select on public.sowia_nex_deals to authenticated", self.sql)

    def test_both_apps_must_be_approved_professional_apps(self):
        self.assertGreaterEqual(self.sql.count("status = 'approved'"), 2)
        self.assertGreaterEqual(self.sql.count("workspace_id = 'professional'"), 2)
        self.assertIn("v_creator_user is distinct from v_actor", self.sql)
        self.assertIn("v_counterparty_user = v_actor", self.sql)

    def test_counterparty_identity_is_derived_from_registry(self):
        self.assertIn("select user_id", self.sql)
        self.assertIn("counterparty_user_id", self.sql)
        self.assertNotIn("p_counterparty_user_id", self.sql)

    def test_non_monetary_deal_has_no_amount_or_commission(self):
        self.assertIn("v_amount <> 0 or p_commission_bps <> 0", self.sql)

    def test_idempotency_rejects_payload_mismatch(self):
        self.assertIn("on conflict (created_by, idempotency_key) do nothing", self.sql)
        self.assertIn("idempotency key reused with a different deal request", self.sql)

    def test_creation_is_additive(self):
        self.assertIn("add column if not exists", self.sql)
        self.assertNotIn("drop table", self.sql)
        self.assertNotIn("truncate", self.sql)


if __name__ == "__main__":
    unittest.main()

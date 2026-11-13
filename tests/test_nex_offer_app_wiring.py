"""Static contract checks for the NIGHT EXCHANGE Streamlit UI wiring."""
import ast
from pathlib import Path
import unittest


class NightExchangeAppWiringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = Path("app.py").read_text(encoding="utf-8")
        cls.tree = ast.parse(source)
        cls.source = source

    def test_proposals_tab_is_present_and_calls_secure_helpers(self):
        self.assertIn('with nex_tab_views[7]:', self.source)
        self.assertIn('cloud_storage.create_night_exchange_offer(', self.source)
        self.assertIn('cloud_storage.list_night_exchange_offers(', self.source)
        self.assertIn('cloud_storage.respond_night_exchange_offer(', self.source)
        self.assertIn('"accepted"', self.source)
        self.assertIn('"rejected"', self.source)

    def test_admin_tab_is_conditionally_rendered_and_uses_admin_rpc_helpers(self):
        self.assertIn('if nex_is_admin:', self.source)
        self.assertIn('with nex_tab_views[8]:', self.source)
        self.assertIn('cloud_storage.list_night_exchange_integrations_for_admin(', self.source)
        self.assertIn('cloud_storage.admin_review_night_exchange_integration(', self.source)

    def test_night_exchange_is_limited_to_professional_workspace(self):
        self.assertIn('st.session_state.get("workspace_id", "professional") != "professional"', self.source)
        self.assertIn('NIGHT EXCHANGE est réservé à l’espace Professionnel', self.source)
        self.assertIn('nex_workspace = "professional"', self.source)

    def test_app_source_parses_as_python(self):
        self.assertIsInstance(self.tree, ast.Module)


if __name__ == "__main__":
    unittest.main()

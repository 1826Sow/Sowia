"""Static contract checks for SOW IA's standard-template email login path."""
import ast
from pathlib import Path
import unittest


class SowiaEmailAuthWiringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = Path("app.py").read_text(encoding="utf-8")
        cls.auth = Path("sowia_supabase_auth.py").read_text(encoding="utf-8")
        cls.app_tree = ast.parse(cls.app)
        cls.auth_tree = ast.parse(cls.auth)

    def test_github_pkce_client_remains_separate(self):
        self.assertIn('flow_type="pkce"', self.auth)
        self.assertIn("create_user_client(browser_id)", self.app)

    def test_email_link_uses_separate_implicit_client(self):
        self.assertIn('flow_type="implicit"', self.auth)
        self.assertIn("create_email_user_client()", self.app)
        self.assertIn("email_magic_link(email_client, email_address, redirect_to)", self.app)

    def test_browser_fragment_is_exchanged_into_supabase_session(self):
        self.assertIn("read_email_auth_fragment()", self.app)
        self.assertIn('supabase_client.auth.set_session(', self.app)
        self.assertIn('token_type == "magiclink"', self.auth)

    def test_both_modules_parse_as_python(self):
        self.assertIsInstance(self.app_tree, ast.Module)
        self.assertIsInstance(self.auth_tree, ast.Module)


if __name__ == "__main__":
    unittest.main()

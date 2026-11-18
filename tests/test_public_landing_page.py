from html.parser import HTMLParser
from pathlib import Path
import re
import unittest


PAGE = Path(__file__).resolve().parents[1] / "public-site" / "index.html"
APP_URL = "https://fm5aczcvvj5jgkhpxwqtcr.streamlit.app/"


class LandingPageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.links = []
        self.languages = []
        self.main_ids = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "a":
            self.links.append(attrs.get("href", ""))
        if tag == "option":
            self.languages.append(attrs.get("value"))
        if tag == "main":
            self.main_ids.append(attrs.get("id"))


class PublicLandingPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = PAGE.read_text(encoding="utf-8")
        cls.parser = LandingPageParser()
        cls.parser.feed(cls.source)

    def test_document_has_language_and_mobile_viewport(self):
        self.assertIn('<html lang="fr">', self.source)
        self.assertIn('name="viewport"', self.source)

    def test_language_selector_has_three_supported_languages(self):
        self.assertEqual(self.parser.languages, ["fr", "en", "es"])
        for lang in ("fr", "en", "es"):
            self.assertRegex(self.source, rf"(?<![a-z]){lang}:\{{")

    def test_main_content_has_skip_link_target(self):
        self.assertIn('href="#main"', self.source)
        self.assertEqual(self.parser.main_ids, ["main"])
        self.assertIn(".skip-link:focus", self.source)

    def test_ids_are_unique(self):
        self.assertEqual(len(self.parser.ids), len(set(self.parser.ids)))

    def test_application_links_use_expected_secure_destination(self):
        app_links = [href for href in self.parser.links if href.startswith("https://")]
        self.assertGreaterEqual(app_links.count(APP_URL), 2)
        self.assertIn('rel="noopener noreferrer"', self.source)

    def test_reduced_motion_is_respected(self):
        self.assertIn("prefers-reduced-motion:reduce", self.source)

    def test_no_secrets_or_analytics_are_embedded(self):
        forbidden = ("SUPABASE_SERVICE_ROLE", "service_role", "GROQ_API_KEY", "OPENAI_API_KEY", "google-analytics")
        for marker in forbidden:
            self.assertNotIn(marker, self.source)


if __name__ == "__main__":
    unittest.main()

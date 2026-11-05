import unittest

from document_comparison import compare_documents, find_possible_differences


class DocumentComparisonTests(unittest.TestCase):
    def test_finds_shared_and_distinctive_terms_accent_insensitively(self):
        result = compare_documents([
            {"title": "A", "extracted_text": "Le contrat prévoit une rémunération et une durée."},
            {"title": "B", "extracted_text": "La remuneration et la durée sont précisées."},
        ])
        self.assertIn("remuneration", result["shared_terms"])
        self.assertIn("duree", result["shared_terms"])
        self.assertEqual(result["document_count"], 2)

    def test_requires_two_to_five_documents(self):
        with self.assertRaises(ValueError):
            compare_documents([{"title": "A", "extracted_text": "texte"}])

    def test_rejects_empty_document(self):
        with self.assertRaises(ValueError):
            compare_documents([
                {"title": "A", "extracted_text": "texte utile"},
                {"title": "B", "extracted_text": "  "},
            ])

    def test_flags_different_numeric_values_on_shared_topic(self):
        results = find_possible_differences([
            {"title": "A", "extracted_text": "Le loyer mensuel est de 900 euros."},
            {"title": "B", "extracted_text": "Le loyer mensuel est de 1200 euros."},
        ])
        self.assertTrue(any("valeurs numériques différentes" in item["reasons"] for item in results))

    def test_flags_affirmative_and_negative_wording(self):
        results = find_possible_differences([
            {"title": "A", "extracted_text": "Le contrat autorise la résiliation immédiate."},
            {"title": "B", "extracted_text": "Le contrat n'autorise pas la résiliation immédiate."},
        ])
        self.assertTrue(any("formulation affirmative/négative différente" in item["reasons"] for item in results))


if __name__ == "__main__":
    unittest.main()

import unittest

from comparison_report import build_comparison_report_pdf


class ComparisonReportTests(unittest.TestCase):
    def test_builds_a_valid_pdf_report(self):
        comparison = {
            "document_count": 2,
            "similarity_percent": 42,
            "shared_term_count": 3,
            "shared_terms": ["contrat", "loyer", "durée"],
            "documents": [
                {"title": "Bail A", "term_count": 12, "distinctive_terms": ["mensuel"]},
                {"title": "Bail B", "term_count": 14, "distinctive_terms": ["annuel"]},
            ],
        }
        differences = [{
            "document_a": "Bail A",
            "excerpt_a": "Le loyer mensuel est de 900 euros.",
            "document_b": "Bail B",
            "excerpt_b": "Le loyer mensuel est de 1 200 euros.",
            "shared_terms": ["loyer", "mensuel"],
            "reasons": ["valeurs numériques différentes"],
        }]
        result = build_comparison_report_pdf(comparison, differences, "05/11/2026 à 10:00")
        self.assertTrue(result.startswith(b"%PDF"))
        self.assertGreater(len(result), 500)

    def test_builds_report_when_no_candidate_difference_exists(self):
        comparison = {
            "document_count": 2, "similarity_percent": 0, "shared_term_count": 0,
            "shared_terms": [], "documents": [],
        }
        result = build_comparison_report_pdf(comparison, [], "05/11/2026 à 10:00")
        self.assertTrue(result.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()

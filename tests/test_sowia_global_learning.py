import unittest

from sowia_global_learning import build_learning_record, summarize_learning, validate_learning_record


class GlobalLearningTests(unittest.TestCase):
    def setUp(self):
        self.decision = {
            "id": "decision-1",
            "title": "Choix du marché pilote",
            "evidence_level": "documented",
            "criteria": [{"key": "impact", "weight": 1.0}],
            "ranked_options": [
                {"name": "Sénégal", "score": 90},
                {"name": "Malaisie", "score": 70},
            ],
            "recommended_option": "Sénégal",
            "decision_status": "recommendation",
            "score_gap": 20,
            "confidence": 72,
            "created_at": "2026-11-10T10:00:00+00:00",
        }

    def test_snapshot_preserves_original_recommendation(self):
        record = build_learning_record(self.decision, "Malaisie", 4, "Pilote concluant")
        self.assertEqual(record["baseline_snapshot"]["recommended_option"], "Sénégal")
        self.assertFalse(record["recommendation_alignment"])
        self.assertEqual(validate_learning_record(record)["outcome_score"], 4)

    def test_rejects_option_not_in_original_decision(self):
        with self.assertRaises(ValueError):
            build_learning_record(self.decision, "Chine", 3)

    def test_rejects_invalid_outcome_score(self):
        with self.assertRaises(ValueError):
            build_learning_record(self.decision, "Sénégal", 6)

    def test_summary_is_descriptive(self):
        rows = [
            {"outcome_score": 5, "recommendation_alignment": True},
            {"outcome_score": 3, "recommendation_alignment": False},
            {"outcome_score": 4, "recommendation_alignment": None},
        ]
        summary = summarize_learning(rows)
        self.assertEqual(summary["evaluated_decisions"], 3)
        self.assertEqual(summary["recommendation_comparisons"], 2)
        self.assertEqual(summary["recommendation_alignment_rate"], 50.0)
        self.assertEqual(summary["average_outcome_score"], 4.0)


if __name__ == "__main__":
    unittest.main()

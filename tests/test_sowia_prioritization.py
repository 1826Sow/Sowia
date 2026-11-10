"""Unit tests for the SOW IA action-prioritization engine."""
import unittest

from sowia_prioritization import evaluate_action, rank_actions


def action(title, **overrides):
    value = {
        "title": title,
        "pillar": "Test",
        "impact": 5,
        "urgency": 5,
        "feasibility": 5,
        "cost_burden": 0,
        "risk_level": 0,
        "compliance": "verified",
    }
    value.update(overrides)
    return value


class PrioritizationTests(unittest.TestCase):
    def test_best_case_scores_one_hundred(self):
        self.assertEqual(evaluate_action(action("A"))["score"], 100.0)

    def test_prohibited_action_is_blocked_even_with_high_score(self):
        result = evaluate_action(action("A", compliance="prohibited"))
        self.assertEqual(result["status"], "Bloquée")
        self.assertTrue(result["blockers"])

    def test_unverified_compliance_requires_human_review(self):
        result = evaluate_action(action("A", compliance="review_required"))
        self.assertEqual(result["status"], "À valider")

    def test_high_risk_requires_human_review(self):
        result = evaluate_action(action("A", risk_level=4.5))
        self.assertEqual(result["status"], "À valider")

    def test_blocked_action_does_not_rank_above_safe_action(self):
        safe = action("Safe")
        blocked = action("Blocked", compliance="prohibited")
        ranked = rank_actions([blocked, safe])
        self.assertEqual([item["title"] for item in ranked], ["Safe", "Blocked"])

    def test_duplicate_titles_are_rejected(self):
        with self.assertRaises(ValueError):
            rank_actions([action("Same"), action("same")])

    def test_out_of_range_score_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_action(action("A", impact=6))



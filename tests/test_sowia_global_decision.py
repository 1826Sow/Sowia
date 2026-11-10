import unittest

from sowia_global_decision import CRITERIA, evaluate_options, validate_saved_decision


def option(name, values, rationale=""):
    keys = list(CRITERIA)
    return {"name": name, "scores": dict(zip(keys, values)), "rationale": rationale}


class GlobalDecisionTests(unittest.TestCase):
    def test_ranks_options_and_recommends_clear_leader(self):
        result = evaluate_options("Choix du marché", [
            option("Marché A", [5, 5, 4, 4, 4]),
            option("Marché B", [2, 3, 3, 2, 2]),
        ], "documented")
        self.assertEqual(result["recommended_option"], "Marché A")
        self.assertEqual(result["decision_status"], "recommendation")
        self.assertGreater(result["ranked_options"][0]["score"], result["ranked_options"][1]["score"])

    def test_close_scores_do_not_force_recommendation(self):
        result = evaluate_options("Choix proche", [
            option("Option A", [4, 4, 4, 4, 4]),
            option("Option B", [4, 4, 4, 4, 4]),
        ])
        self.assertIsNone(result["recommended_option"])
        self.assertEqual(result["decision_status"], "close_call")

    def test_rejects_invalid_options_and_scores(self):
        with self.assertRaises(ValueError):
            evaluate_options("Sujet", [option("Seule", [3] * 5)])
        with self.assertRaises(ValueError):
            evaluate_options("Sujet", [option("A", [6] * 5), option("B", [3] * 5)])

    def test_saved_decision_schema(self):
        result = evaluate_options("Sujet", [option("A", [5] * 5), option("B", [2] * 5)])
        self.assertEqual(validate_saved_decision(result)["title"], "Sujet")
        result["ranked_options"] = []
        with self.assertRaises(ValueError):
            validate_saved_decision(result)


if __name__ == "__main__":
    unittest.main()

import unittest
from sowia_global_action_governance import validate_action_plan, validate_transition


class ActionGovernanceTests(unittest.TestCase):
    def plan(self, **updates):
        data = dict(title="Pilote Sénégal", objective="Tester le marché avec un périmètre limité.",
                    country="Sénégal", owner_label="Équipe développement", approver_id="123e4567-e89b-12d3-a456-426614174000", budget_cap=500,
                    currency="EUR", due_date="2027-03-31",
                    success_metric="100 utilisateurs actifs", stop_condition="Arrêt si dépassement du plafond.")
        data.update(updates)
        return validate_action_plan(**data)

    def test_valid_plan(self):
        self.assertEqual(self.plan()["budget_cap"], 500.0)

    def test_negative_budget_rejected(self):
        with self.assertRaises(ValueError):
            self.plan(budget_cap=-1)

    def test_non_finite_budgets_rejected(self):
        for budget in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(budget=budget):
                with self.assertRaises(ValueError):
                    self.plan(budget_cap=budget)

    def test_unknown_currency_rejected(self):
        with self.assertRaises(ValueError):
            self.plan(currency="XXX")

    def test_creator_cannot_approve_own_plan(self):
        with self.assertRaises(PermissionError):
            validate_transition("submitted", "approved", True, True)

    def test_second_person_can_approve(self):
        self.assertTrue(validate_transition("submitted", "approved", False, True))

    def test_unapproved_plan_cannot_complete(self):
        with self.assertRaises(PermissionError):
            validate_transition("submitted", "completed", True, False)


if __name__ == "__main__":
    unittest.main()

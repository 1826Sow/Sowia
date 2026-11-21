import unittest

import pytest
from decimal import Decimal

from night_exchange_economy import (
    ApplicationActor, EconomyError, ServiceOrder, discover_matches,
    propose_exchange,
)


class ApplicationEconomyTests(unittest.TestCase):
    def setUp(self):
        self.payment = ApplicationActor(
            app_id="payment-app", name="Payment App", owner_id="owner-a",
            capabilities=("payments-api",), services_offered=("payment processing",),
            services_wanted=("fraud checks",), approved=True,
        )
        self.transport = ApplicationActor(
            app_id="transport-app", name="Transport App", owner_id="owner-b",
            capabilities=("booking",), services_offered=("rides",),
            services_wanted=("payment processing",), approved=True,
        )

    def test_applications_match_service_orders(self):
        orders = [
            ServiceOrder("offer-1", "payment-app", "offer",
                         "payment processing", Decimal("10"), Decimal("0.20"), "EUR"),
            ServiceOrder("request-1", "transport-app", "request",
                         "payment processing", Decimal("8"), Decimal("0.25"), "EUR"),
        ]
        matches = discover_matches([self.payment, self.transport], orders)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["provider_app_id"], "payment-app")
        self.assertEqual(matches[0]["client_app_id"], "transport-app")
        self.assertEqual(matches[0]["quantity"], Decimal("8.00"))
        self.assertEqual(matches[0]["total"], Decimal("1.60"))

    def test_unapproved_application_is_not_matched(self):
        unapproved = ApplicationActor(
            app_id="unapproved", name="Unapproved", owner_id="owner-c",
            capabilities=("api",), services_offered=("payment processing",),
            services_wanted=(), approved=False,
        )
        orders = [
            ServiceOrder("offer-1", "unapproved", "offer",
                         "payment processing", 1, 1, "EUR"),
            ServiceOrder("request-1", "transport-app", "request",
                         "payment processing", 1, 2, "EUR"),
        ]
        self.assertEqual(discover_matches([unapproved, self.transport], orders), [])

    def test_currency_mismatch_is_not_matched(self):
        orders = [
            ServiceOrder("offer-1", "payment-app", "offer",
                         "payment processing", 1, 1, "USD"),
            ServiceOrder("request-1", "transport-app", "request",
                         "payment processing", 1, 2, "EUR"),
        ]
        self.assertEqual(discover_matches([self.payment, self.transport], orders), [])

    def test_proposal_requires_owner_approval_and_never_executes(self):
        orders = [
            ServiceOrder("offer-1", "payment-app", "offer",
                         "payment processing", 10, "0.20", "EUR"),
            ServiceOrder("request-1", "transport-app", "request",
                         "payment processing", 8, "0.25", "EUR"),
        ]
        proposal = propose_exchange(discover_matches(
            [self.payment, self.transport], orders
        )[0])
        self.assertEqual(proposal.state, "awaiting_owner_approval")
        self.assertTrue(proposal.simulation)

    def test_inconsistent_total_is_rejected(self):
        orders = [
            ServiceOrder("offer-1", "payment-app", "offer",
                         "payment processing", 10, "0.20", "EUR"),
            ServiceOrder("request-1", "transport-app", "request",
                         "payment processing", 8, "0.25", "EUR"),
        ]
        match = discover_matches([self.payment, self.transport], orders)[0]
        match["total"] = Decimal("99")
        with self.assertRaises(EconomyError):
            propose_exchange(match)

    def test_invalid_currency_is_rejected(self):
        with self.assertRaises(EconomyError):
            ServiceOrder("x", "payment-app", "offer", "api", 1, 1, "EURO")


if __name__ == "__main__":
    unittest.main()



def test_discover_service_partners_returns_only_approved_exact_service_matches():
    from night_exchange_economy import discover_service_partners

    rows = [
        {"id": "app-a", "app_name": "Initiator", "services_offered": "rides",
         "services_wanted": "payment processing", "status": "approved"},
        {"id": "app-b", "app_name": "Payment API", "country": "France",
         "services_offered": "payment processing, fraud checks", "status": "approved"},
        {"id": "app-c", "app_name": "Pending API",
         "services_offered": "payment processing", "status": "pending"},
        {"id": "app-d", "app_name": "Different API",
         "services_offered": "payment gateway", "status": "approved"},
    ]
    matches = discover_service_partners("app-a", "payment processing", rows)
    assert [item["app_id"] for item in matches] == ["app-b"]
    assert matches[0]["simulation"] is True


def test_discover_service_partners_excludes_source_and_rejects_empty_service():
    from night_exchange_economy import discover_service_partners

    rows = [{"id": "app-a", "services_offered": "payment processing",
             "status": "approved"}]
    assert discover_service_partners("app-a", "payment processing", rows) == []
    with pytest.raises(EconomyError):
        discover_service_partners("app-a", " ", rows)

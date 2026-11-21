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
         "services_wanted": "translation", "status": "approved"},
        {"id": "app-b", "app_name": "Payment API", "country": "France",
         "services_offered": "translation, fraud checks", "status": "approved", "owner_verification_status": "verified", "application_verification_status": "verified", "security_review_status": "passed", "publisher_signature_status": "verified"},
        {"id": "app-c", "app_name": "Pending API",
         "services_offered": "translation", "status": "pending"},
        {"id": "app-d", "app_name": "Different API",
         "services_offered": "payment gateway", "status": "approved", "owner_verification_status": "verified", "application_verification_status": "verified", "security_review_status": "passed", "publisher_signature_status": "verified"},
    ]
    matches = discover_service_partners("app-a", "translation", rows)
    assert [item["app_id"] for item in matches] == ["app-b"]
    assert matches[0]["simulation"] is True


def test_discover_service_partners_excludes_source_and_rejects_empty_service():
    from night_exchange_economy import discover_service_partners

    rows = [{"id": "app-a", "services_offered": "payment processing",
             "status": "approved"}]
    assert discover_service_partners("app-a", "payment processing", rows) == []
    with pytest.raises(EconomyError):
        discover_service_partners("app-a", " ", rows)



def test_partner_discovery_fails_closed_for_missing_or_unknown_approval():
    from night_exchange_economy import discover_service_partners

    rows = [
        {"id": "missing-status", "app_name": "Unknown", "services_offered": "translation"},
        {"id": "pending", "app_name": "Pending", "status": "pending",
         "services_offered": "translation"},
        {"id": "approved", "app_name": "Approved", "status": "approved",
         "services_offered": "translation"},
    ]
    matches = discover_service_partners("source", "translation", rows)
    assert matches == []


def test_partner_discovery_supports_list_declarations_and_disabled_filter():
    from night_exchange_economy import discover_service_partners

    rows = [
        {"id": "enabled", "app_name": "Enabled", "status": "approved",
         "enabled": True, "owner_verification_status": "verified",
         "application_verification_status": "verified", "security_review_status": "passed",
         "publisher_signature_status": "verified",
         "services_offered": [" Data Analysis ", "translation"]},
        {"id": "disabled", "app_name": "Disabled", "status": "approved",
         "enabled": False, "services_offered": ["data analysis"]},
    ]
    matches = discover_service_partners("source", "data analysis", rows)
    assert [item["app_id"] for item in matches] == ["enabled"]


def test_partner_discovery_exposes_explainable_match_and_verification_state():
    from night_exchange_economy import discover_service_partners

    rows = [{
        "id": "provider", "app_name": "Provider", "status": "approved",
        "verification_status": "verified",
        "owner_verification_status": "verified",
        "application_verification_status": "verified",
        "security_review_status": "passed",
        "publisher_signature_status": "verified",
        "categories": ["AI", "Data"],
        "services_offered": "data analysis",
    }]
    match = discover_service_partners("source", "data analysis", rows)[0]
    assert match["match_type"] == "canonical_skill"
    assert match["match_reasons"]
    assert match["verification_state"] == "verified"
    assert match["simulation"] is True


def test_partner_discovery_does_not_admit_approval_without_security_evidence():
    from night_exchange_economy import discover_service_partners

    rows = [{
        "id": "provider", "app_name": "Provider", "status": "approved",
        "services_offered": "data analysis",
    }]
    assert discover_service_partners("source", "data analysis", rows) == []


def test_shared_skill_catalog_is_versioned_and_requires_human_approval():
    from night_exchange_economy import SKILL_CATALOG_VERSION, list_skill_catalog

    catalog = list_skill_catalog()
    assert catalog
    assert all(item["catalog_version"] == SKILL_CATALOG_VERSION for item in catalog)
    assert all(item["human_approval_required"] is True for item in catalog)
    assert len({item["skill_id"] for item in catalog}) == len(catalog)


def test_skill_resolution_maps_aliases_to_same_canonical_skill():
    from night_exchange_economy import resolve_service_skill

    english = resolve_service_skill("data analysis")
    french = resolve_service_skill("Analyse de données")
    assert english["skill_id"] == french["skill_id"] == "data.analysis"
    assert english["category_id"] == "data_analytics"


def test_unknown_skill_is_not_guessed():
    from night_exchange_economy import resolve_service_skill

    assert resolve_service_skill("quantum dragon orchestration") is None
    assert resolve_service_skill("") is None


def test_restricted_financial_services_are_not_in_initial_skill_catalog():
    from night_exchange_economy import resolve_service_skill

    assert resolve_service_skill("payment processing") is None
    assert resolve_service_skill("transfert d'argent") is None


def test_partner_discovery_matches_known_skill_aliases_and_explains_reason():
    from night_exchange_economy import discover_service_partners

    rows = [{
        "id": "provider", "app_name": "Analytica", "status": "approved",
        "owner_verification_status": "verified",
        "application_verification_status": "verified",
        "security_review_status": "passed",
        "publisher_signature_status": "verified",
        "enabled": True, "security_suspended": False,
        "services_offered": "Analyse de données",
    }]
    match = discover_service_partners("requester", "data analysis", rows)[0]
    assert match["match_type"] == "canonical_skill"
    assert match["skill"]["skill_id"] == "data.analysis"
    assert match["matched_service"] == "analyse de données"
    assert "compétence normalisée" in match["match_reasons"][0]


def test_partner_discovery_keeps_custom_services_exact_only():
    from night_exchange_economy import discover_service_partners

    rows = [{
        "id": "provider", "app_name": "Custom", "status": "approved",
        "owner_verification_status": "verified",
        "application_verification_status": "verified",
        "security_review_status": "passed",
        "publisher_signature_status": "verified",
        "enabled": True, "security_suspended": False,
        "services_offered": "bespoke legacy connector",
    }]
    assert discover_service_partners("requester", "bespoke legacy connector", rows)
    assert discover_service_partners("requester", "legacy connector", rows) == []


def test_partner_discovery_excludes_restricted_financial_services_even_as_custom_labels():
    from night_exchange_economy import discover_service_partners

    rows = [{
        "id": "payment-provider", "app_name": "Payment Provider",
        "status": "approved", "services_offered": "payment processing",
    }]
    assert discover_service_partners("requester", "payment processing", rows) == []


def test_partner_admission_fails_closed_without_independent_security_evidence():
    from night_exchange_economy import assess_partner_admission

    record = {"status": "approved", "services_offered": "translation"}
    result = assess_partner_admission(record)
    assert result["eligible"] is False
    assert "owner_identity_verified" in result["failed_checks"]
    assert "security_review_passed" in result["failed_checks"]


def test_partner_admission_requires_all_independent_verification_gates():
    from night_exchange_economy import assess_partner_admission

    record = {
        "status": "approved",
        "owner_verification_status": "verified",
        "application_verification_status": "verified",
        "security_review_status": "passed",
        "publisher_signature_status": "verified",
        "enabled": True,
        "security_suspended": False,
    }
    assert assess_partner_admission(record)["eligible"] is True
    record["publisher_signature_status"] = "unknown"
    assert assess_partner_admission(record)["eligible"] is False


def test_partner_admission_rejects_suspended_or_disabled_apps():
    from night_exchange_economy import assess_partner_admission

    record = {
        "status": "approved",
        "owner_verification_status": "verified",
        "application_verification_status": "verified",
        "security_review_status": "passed",
        "publisher_signature_status": "verified",
        "enabled": True,
        "security_suspended": False,
    }
    record["security_suspended"] = True
    assert assess_partner_admission(record)["eligible"] is False
    record["security_suspended"] = False
    record["enabled"] = False
    assert assess_partner_admission(record)["eligible"] is False


def test_discovery_excludes_approved_but_unverified_or_unsigned_apps():
    from night_exchange_economy import discover_service_partners

    rows = [{
        "id": "fake-app", "app_name": "Fake", "status": "approved",
        "services_offered": "translation",
    }]
    assert discover_service_partners("requester", "translation", rows) == []


def test_discovery_requires_all_security_evidence_before_listing_partner():
    from night_exchange_economy import discover_service_partners

    rows = [{
        "id": "trusted-app", "app_name": "Trusted", "status": "approved",
        "owner_verification_status": "verified",
        "application_verification_status": "verified",
        "security_review_status": "passed",
        "publisher_signature_status": "verified",
        "enabled": True, "security_suspended": False,
        "services_offered": "translation",
    }]
    assert len(discover_service_partners("requester", "translation", rows)) == 1

def test_market_snapshot_counts_only_declared_catalogue_activity():
    from night_exchange_economy import summarize_market_snapshot

    snapshot = summarize_market_snapshot([
        {"id": "a", "services_offered": "translation, data analysis",
         "services_wanted": "research", "country": "France"},
        {"id": "b", "services_offered": ["translation"], "services_wanted": "",
         "country": " France "},
        {"id": "c", "services_offered": "", "services_wanted": ["design"],
         "country": "Canada"},
        None,
        {"id": "d", "services_offered": 42, "services_wanted": None},
    ])
    assert snapshot == {
        "listed_applications": 4,
        "service_providers": 2,
        "applications_with_needs": 2,
        "distinct_declared_services": 3,
        "countries_represented": 2,
        "market_share_available": False,
        "revenue_available": False,
    }


def test_market_snapshot_does_not_invent_market_share_or_revenue():
    from night_exchange_economy import summarize_market_snapshot

    snapshot = summarize_market_snapshot([])
    assert snapshot["market_share_available"] is False
    assert snapshot["revenue_available"] is False

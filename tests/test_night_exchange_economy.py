undefined

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

import pytest

from business_revenue import (
    NICHE_CATEGORIES, STAGES, opportunity_metrics, validate_opportunity,
)


def test_validate_opportunity_normalizes_amounts_and_source():
    row = validate_opportunity(
        NICHE_CATEGORIES[0], "Assistant administratif", STAGES[0],
        "1250,50", "200", "EUR", "https://example.com/market",
    )
    assert row["expected_monthly_revenue"] == 1250.50
    assert row["estimated_monthly_cost"] == 200.0
    assert row["source_url"] == "https://example.com/market"


@pytest.mark.parametrize("url", ["javascript:alert(1)", "file:///etc/passwd", "not-a-url"])
def test_validate_opportunity_rejects_unsafe_source(url):
    with pytest.raises(ValueError, match="URL HTTP"):
        validate_opportunity(NICHE_CATEGORIES[0], "Offre", STAGES[0], 100, 10, source_url=url)


def test_validate_opportunity_rejects_negative_and_invalid_stage():
    with pytest.raises(ValueError):
        validate_opportunity(NICHE_CATEGORIES[0], "Offre", STAGES[0], -1, 10)
    with pytest.raises(ValueError):
        validate_opportunity(NICHE_CATEGORIES[0], "Offre", "Envoyée", 100, 10)


def test_metrics_separate_active_pipeline_and_currencies():
    items = [
        {"stage": "Active", "expected_monthly_revenue": 1000, "estimated_monthly_cost": 100, "currency": "EUR"},
        {"stage": "À tester", "expected_monthly_revenue": 500, "estimated_monthly_cost": 80, "currency": "EUR"},
        {"stage": "Abandonnée", "expected_monthly_revenue": 9000, "estimated_monthly_cost": 0, "currency": "EUR"},
        {"stage": "Active", "expected_monthly_revenue": 200, "estimated_monthly_cost": 20, "currency": "USD"},
    ]
    result = opportunity_metrics(items)
    assert result["total"] == 4
    assert result["active"] == 2
    assert result["by_currency"]["EUR"]["forecast_monthly"] == 1500
    assert result["by_currency"]["EUR"]["active_forecast_monthly"] == 1000
    assert result["by_currency"]["USD"]["forecast_monthly"] == 200
    assert result["confirmed_revenue"] == 0

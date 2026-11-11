import math
import pytest

from hedge_fund_intelligence import (
    analyze_monthly_net_returns,
    normalize_hedge_fund_profile,
)


def valid_profile(**overrides):
    raw = {
        "fund_id": "HF-001",
        "name": "Example Global Fund",
        "manager": "Example Management",
        "strategy": "global_macro",
        "domicile": "Cayman Islands",
        "base_currency": "USD",
        "aum": 125000000.0,
        "aum_as_of": "2026-09-30",
        "source_url": "https://example.com/factsheet",
        "source_verified": True,
    }
    raw.update(overrides)
    return raw


def test_normalize_profile_preserves_currency_and_source_status():
    profile = normalize_hedge_fund_profile(valid_profile())
    assert profile.base_currency == "USD"
    assert profile.aum == 125000000.0
    assert profile.source_verified is True


@pytest.mark.parametrize("overrides", [
    {"strategy": "guaranteed_profit"},
    {"base_currency": "US"},
    {"aum": -1},
    {"aum": float("nan")},
    {"aum": 10, "aum_as_of": None},
    {"source_url": "http://example.com/factsheet"},
    {"source_verified": True, "source_url": None},
    {"source_verified": "yes"},
])
def test_profile_rejects_invalid_or_unverifiable_fields(overrides):
    with pytest.raises(ValueError):
        normalize_hedge_fund_profile(valid_profile(**overrides))


def test_monthly_returns_calculate_compound_return_and_drawdown():
    result = analyze_monthly_net_returns([
        {"month": "2026-01-01", "net_return": 0.10},
        {"month": "2026-02-01", "net_return": -0.10},
    ])
    assert result.observations == 2
    assert result.cumulative_return_pct == pytest.approx(-1.0)
    assert result.maximum_drawdown_pct == pytest.approx(10.0)
    assert result.annualized_volatility_pct is not None
    assert result.sharpe_ratio is not None


def test_single_observation_does_not_invent_volatility_or_sharpe():
    result = analyze_monthly_net_returns([
        {"month": "2026-01-01", "net_return": 0.02},
    ])
    assert result.annualized_volatility_pct is None
    assert result.sharpe_ratio is None


@pytest.mark.parametrize("observations", [
    [],
    [{"month": "2026-01-01", "net_return": -1.0}],
    [{"month": "2026-01-01", "net_return": float("inf")}],
    [
        {"month": "2026-01-01", "net_return": 0.01},
        {"month": "2026-01-01", "net_return": 0.02},
    ],
    [
        {"month": "2026-01-01", "net_return": 0.01},
        {"month": "2026-03-01", "net_return": 0.02},
    ],
])
def test_returns_reject_empty_invalid_duplicate_or_missing_months(observations):
    with pytest.raises(ValueError):
        analyze_monthly_net_returns(observations)


def test_returns_are_sorted_by_month_before_analysis():
    result = analyze_monthly_net_returns([
        {"month": "2026-02-01", "net_return": 0.02},
        {"month": "2026-01-01", "net_return": 0.01},
    ])
    assert result.first_month.isoformat() == "2026-01-01"
    assert result.last_month.isoformat() == "2026-02-01"


def test_risk_free_rate_must_be_finite_and_above_minus_100_percent():
    with pytest.raises(ValueError):
        analyze_monthly_net_returns(
            [{"month": "2026-01-01", "net_return": 0.01}],
            risk_free_rate_annual_pct=-100,
        )
    with pytest.raises(ValueError):
        analyze_monthly_net_returns(
            [{"month": "2026-01-01", "net_return": 0.01}],
            risk_free_rate_annual_pct=math.inf,
        )

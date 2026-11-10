import pytest

from strategic_scenarios import SCENARIO_WEIGHTS, evaluate_scenario, rank_scenarios


def good_scores(**overrides):
    values = {key: 4.5 for key in SCENARIO_WEIGHTS}
    values.update(overrides)
    return values


def test_legal_prohibition_blocks_even_high_score():
    result = evaluate_scenario(
        "Scénario interdit", "rupture", good_scores(),
        legal_state="prohibited",
    )
    assert result.decision == "Bloqué"
    assert result.requires_human_approval


def test_legal_review_required_prevents_pilot():
    result = evaluate_scenario("Nouvelle offre", "acceleration", good_scores())
    assert result.decision == "Validation juridique requise"


def test_verified_low_risk_reversible_scenario_can_be_considered_for_pilot():
    result = evaluate_scenario(
        "Optimisation interne", "prudent", good_scores(),
        legal_state="verified", risk_level="low",
    )
    assert result.decision == "Pilote limité envisageable"
    assert not result.requires_human_approval


@pytest.mark.parametrize("kwargs", [
    {"external_impact": True},
    {"spending_required": True},
    {"production_change": True},
    {"risk_level": "high"},
])
def test_sensitive_actions_require_human_approval(kwargs):
    result = evaluate_scenario(
        "Déploiement", "acceleration", good_scores(),
        legal_state="verified", risk_level=kwargs.pop("risk_level", "low"),
        **kwargs,
    )
    assert result.decision == "Validation humaine obligatoire"
    assert result.requires_human_approval


def test_invalid_inputs_are_rejected():
    with pytest.raises(ValueError):
        evaluate_scenario("", "prudent", good_scores())
    with pytest.raises(ValueError):
        evaluate_scenario("A", "unknown", good_scores())
    with pytest.raises(ValueError):
        evaluate_scenario("A", "prudent", good_scores(strategic_fit=6))


def test_ranking_puts_blocked_scenarios_last():
    pilot = evaluate_scenario(
        "Pilote", "prudent", good_scores(),
        legal_state="verified", risk_level="low",
    )
    blocked = evaluate_scenario(
        "Bloqué", "rupture", good_scores(), legal_state="prohibited",
    )
    assert [item.name for item in rank_scenarios([blocked, pilot])] == ["Pilote", "Bloqué"]

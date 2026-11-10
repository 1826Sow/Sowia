import pytest

from decision_lab import create_decision_record, evaluate_decision_outcomes, CRITERIA


def option(name, score=4, legal="verified", risk="low"):
    return {
        "name": name,
        "scores": {key: score for key in CRITERIA},
        "legal_state": legal,
        "risk_level": risk,
    }


def test_ai_choice_is_ranked_only_among_eligible_options():
    record = create_decision_record(
        title="Choix stratégique", question="Quelle option retenir ?",
        context="Test", human_choice="Option A",
        options=[option("Option A", 3), option("Option B", 5),
                 option("Option C", 5, legal="prohibited")],
    )
    assert record["ai_choice"] == "Option B"
    assert record["decision_hash"] and len(record["decision_hash"]) == 64


def test_no_ai_choice_when_all_options_fail_gates():
    record = create_decision_record(
        title="Test", question="Choix ?", context="", human_choice="A",
        options=[option("A", legal="review_required"), option("B", risk="critical")],
    )
    assert record["ai_choice"] is None


def test_outcome_comparison_uses_actual_result_of_each_option():
    record = create_decision_record(
        title="Test", question="Choix ?", context="", human_choice="A",
        options=[option("A", 3), option("B", 5)],
    )
    result = evaluate_decision_outcomes(record, {"A": 72, "B": 91})
    assert result["winner"] == "Décision SOW IA"
    assert result["difference"] == 19


def test_outcome_requires_every_option_and_bounded_values():
    record = create_decision_record(
        title="Test", question="Choix ?", context="", human_choice="A",
        options=[option("A"), option("B")],
    )
    with pytest.raises(ValueError):
        evaluate_decision_outcomes(record, {"A": 40})
    with pytest.raises(ValueError):
        evaluate_decision_outcomes(record, {"A": 120, "B": 20})


def test_duplicate_option_names_are_rejected():
    with pytest.raises(ValueError):
        create_decision_record(
            title="Test", question="Choix ?", context="", human_choice="A",
            options=[option("A"), option("a")],
        )

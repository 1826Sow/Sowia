from decision_statistics import summarize_decisions


def test_statistics_only_include_completed_comparable_trials():
    result = summarize_decisions([
        {"human_choice": "A", "ai_choice": "B", "outcomes": {"A": 60, "B": 80}, "category": "Finance"},
        {"human_choice": "A", "ai_choice": "B", "outcomes": {"A": 90, "B": 70}, "category": "Finance"},
        {"human_choice": "A", "ai_choice": None, "outcomes": None},
    ])
    overall = result["overall"]
    assert overall["sample_size"] == 2
    assert overall["ai_wins"] == 1
    assert overall["human_wins"] == 1
    assert overall["mean_ai_minus_human"] == 0
    assert result["excluded_incomplete"] == 1
    assert result["by_category"]["Finance"]["sample_size"] == 2


def test_statistics_handle_ties_and_empty_data():
    result = summarize_decisions([
        {"human_choice": "A", "ai_choice": "B", "outcomes": {"A": 75, "B": 75}}
    ])
    assert result["overall"]["ties"] == 1
    assert result["overall"]["tie_rate_pct"] == 100
    empty = summarize_decisions([])
    assert empty["overall"]["sample_size"] == 0
    assert empty["overall"]["ai_win_rate_pct"] is None

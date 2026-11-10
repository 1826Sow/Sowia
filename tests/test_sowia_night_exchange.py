from datetime import datetime, timezone
import pytest
from sowia_night_exchange import AppListing, BudgetCap, NightExchangeError, is_local_night, match_apps, select_budgeted_offers

def test_timezone_night_window():
    assert is_local_night(datetime(2026, 1, 10, 21, tzinfo=timezone.utc), "Europe/Paris")
    assert not is_local_night(datetime(2026, 1, 10, 10, tzinfo=timezone.utc), "Europe/Paris")

def test_invalid_datetime_and_timezone():
    with pytest.raises(NightExchangeError):
        is_local_night(datetime(2026, 1, 1, 22), "Europe/Paris")
    with pytest.raises(NightExchangeError):
        is_local_night(datetime.now(timezone.utc), "Mars/Imaginary")

def test_budget_caps():
    cap = BudgetCap.create("EUR", "10", "30", "100")
    assert cap.authorize("10")
    cap.record_confirmed_spend("8")
    assert not cap.authorize("3")
    with pytest.raises(NightExchangeError):
        cap.record_confirmed_spend("3")

def test_budget_order():
    with pytest.raises(NightExchangeError):
        BudgetCap.create("EUR", 20, 10, 100)

def test_matching_requires_approval():
    source = AppListing("a", "A", "FR", "Europe/Paris", ("AI",), ("translation",), ("payments",), True, True)
    good = AppListing("b", "B", "SG", "Asia/Singapore", ("AI",), ("payments",), ("translation",), True, True)
    pending = AppListing("c", "C", "SG", "Asia/Singapore", ("AI",), ("payments",), ("translation",), True, False)
    matches = match_apps(source, [pending, good])
    assert [m.app_id for m in matches] == ["b"]
    assert matches[0].reciprocal_exchange

def test_budgeted_offers_are_capped_and_deterministic():
    offers = [{"offer_id":"b","price":"7","relevance_score":90},
              {"offer_id":"a","price":"5","relevance_score":90},
              {"offer_id":"c","price":"20","relevance_score":100}]
    assert [x["offer_id"] for x in select_budgeted_offers(offers, "12")] == ["c"]

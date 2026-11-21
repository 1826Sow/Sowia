import pytest


def test_night_exchange_listing_validation_accepts_global_timezone():
    from cloud_storage import _validate_night_exchange_listing
    listing = _validate_night_exchange_listing(
        "App partenaire", "Singapour", "Asia/Singapore",
        ["Productivité"], "API de traduction", "Paiements", "21:00", "05:00"
    )
    assert listing["timezone"] == "Asia/Singapore"
    assert listing["night_start"] == "21:00"
    assert listing["night_end"] == "05:00"


def test_night_exchange_listing_validation_rejects_unknown_timezone():
    from cloud_storage import _validate_night_exchange_listing
    with pytest.raises(ValueError):
        _validate_night_exchange_listing(
            "App partenaire", "France", "Mars/Imaginary", ["Productivité"]
        )


def test_night_exchange_listing_validation_requires_category():
    from cloud_storage import _validate_night_exchange_listing
    with pytest.raises(ValueError):
        _validate_night_exchange_listing(
            "App partenaire", "France", "Europe/Paris", []
        )


def test_matching_uses_only_approved_candidates_and_ranks_reciprocal_exchange():
    from sowia_night_exchange import match_listing_records

    source = {
        "id": "app-a",
        "status": "approved",
        "categories": ["Productivité", "Finance"],
        "services_offered": ["API de paiement"],
        "services_wanted": ["Traduction"],
    }
    candidates = [
        {
            "id": "app-b",
            "status": "approved",
            "verified": True,
            "categories": ["Finance"],
            "services_offered": ["Traduction"],
            "services_wanted": ["API de paiement"],
        },
        {
            "id": "app-c",
            "status": "pending",
            "verified": True,
            "categories": ["Finance"],
            "services_offered": ["Traduction"],
            "services_wanted": ["API de paiement"],
        },
        {
            "id": "app-a",
            "status": "approved",
            "categories": ["Finance"],
            "services_offered": ["Traduction"],
            "services_wanted": ["API de paiement"],
        },
    ]

    matches = match_listing_records(source, candidates)

    assert [match.app_id for match in matches] == ["app-b"]
    assert matches[0].reciprocal_exchange is True
    assert matches[0].shared_categories == ("finance",)


def test_budgeted_offer_selection_respects_budget_and_relevance_order():
    from sowia_night_exchange import select_budgeted_offers

    offers = [
        {"offer_id": "too-expensive", "price": "12.00", "relevance_score": 100},
        {"offer_id": "best-fit", "price": "8.00", "relevance_score": 90},
        {"offer_id": "fills-budget", "price": "2.00", "relevance_score": 70},
    ]

    selected = select_budgeted_offers(offers, "10.00")

    assert [offer["offer_id"] for offer in selected] == ["best-fit", "fills-budget"]


def test_budgeted_offer_selection_rejects_invalid_score_and_negative_price():
    from sowia_night_exchange import NightExchangeError, select_budgeted_offers

    with pytest.raises(NightExchangeError):
        select_budgeted_offers(
            [{"offer_id": "bad-score", "price": "1.00", "relevance_score": 101}],
            "10.00",
        )
    with pytest.raises(NightExchangeError):
        select_budgeted_offers(
            [{"offer_id": "negative", "price": "-1.00", "relevance_score": 50}],
            "10.00",
        )


def test_budget_cap_enforces_daily_weekly_and_monthly_limits():
    from decimal import Decimal
    from sowia_night_exchange import BudgetCap, NightExchangeError

    cap = BudgetCap.create("EUR", "10.00", "20.00", "50.00")
    assert cap.authorize("10.00") is True
    cap.record_confirmed_spend("10.00")
    assert cap.spent_today == Decimal("10.00")
    assert cap.authorize("0.01") is False

    cap.reset_period("day")
    assert cap.authorize("10.00") is True

    with pytest.raises(NightExchangeError):
        BudgetCap.create("EUR", "20.00", "10.00", "50.00")


def test_global_session_status_uses_listing_local_timezone():
    from datetime import datetime, timezone
    from sowia_night_exchange import global_session_status

    listing = {
        "timezone": "Asia/Singapore",
        "night_start": "20:00",
        "night_end": "06:00",
    }
    active = global_session_status(
        listing, datetime(2026, 11, 21, 13, 30, tzinfo=timezone.utc)
    )
    closed = global_session_status(
        listing, datetime(2026, 11, 21, 3, 0, tzinfo=timezone.utc)
    )

    assert active["is_open"] is True
    assert active["timezone"] == "Asia/Singapore"
    assert closed["is_open"] is False
    assert closed["next_open_local"].strftime("%Y-%m-%d %H:%M") == "2026-11-21 20:00"

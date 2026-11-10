from datetime import datetime, timezone
from decimal import Decimal

import pytest

import sowia_night_exchange as nex


def test_global_session_status_uses_partner_local_timezone():
    now = datetime(2026, 1, 15, 13, 0, tzinfo=timezone.utc)
    result = nex.global_session_status({
        "timezone": "Asia/Singapore",
        "night_start": "20:00",
        "night_end": "06:00",
    }, now)
    assert result["is_open"] is True
    assert result["local_now"].hour == 21
    assert result["next_open_utc"] is None


def test_global_session_status_returns_next_opening_in_utc():
    now = datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc)
    result = nex.global_session_status({
        "timezone": "Europe/Paris",
        "night_start": "20:00",
        "night_end": "06:00",
    }, now)
    assert result["is_open"] is False
    assert result["next_open_local"].hour == 20
    assert result["next_open_utc"].hour == 19


def test_global_session_status_rejects_naive_datetime():
    with pytest.raises(nex.NightExchangeError):
        nex.global_session_status({"timezone": "UTC"}, datetime(2026, 1, 15, 10, 0))


def test_smart_opportunities_explain_reciprocal_services():
    source = {
        "id": "source", "app_name": "Source", "status": "approved",
        "categories": ["Commerce"], "services_offered": "API paiement",
        "services_wanted": "Traduction",
    }
    partner = {
        "id": "partner", "app_name": "Partner", "country": "Singapore",
        "status": "approved", "categories": ["Commerce"],
        "services_offered": "Traduction", "services_wanted": "API paiement",
    }
    result = nex.build_smart_opportunities(source, [partner])
    assert len(result) == 1
    assert result[0]["reciprocal_exchange"] is True
    assert result[0]["signals"]["partner_services_matching_my_needs"] == ["traduction"]
    assert result[0]["signals"]["my_services_matching_partner_needs"] == ["api paiement"]


def test_smart_opportunities_reject_invalid_limit():
    with pytest.raises(nex.NightExchangeError):
        nex.build_smart_opportunities({}, [], limit=0)


def test_morning_report_counts_only_confirmed_payment():
    report = nex.build_morning_report([
        {"event_type": "match_viewed"},
        {"event_type": "payment_confirmed", "payment_status": "pending", "amount": "99", "currency": "EUR"},
        {"event_type": "payment_confirmed", "payment_status": "confirmed", "amount": "12.50", "currency": "EUR"},
    ])
    assert report["counts"]["match_viewed"] == 1
    assert report["counts"]["payment_confirmed"] == 1
    assert report["confirmed_spend"] == Decimal("12.50")
    assert report["spend_currencies"] == ["EUR"]


def test_morning_report_does_not_infer_events():
    report = nex.build_morning_report([])
    assert report["recognized_events"] == 0
    assert report["has_recorded_activity"] is False

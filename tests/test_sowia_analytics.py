from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sowia_analytics import aggregate_events, record_event


def test_aggregate_counts_unique_android_installs_and_active_users():
    now = datetime(2026, 11, 18, 12, 0, tzinfo=timezone.utc)
    user_a, user_b = str(uuid4()), str(uuid4())
    install_a, install_b = str(uuid4()), str(uuid4())
    events = [
        {"event_type": "android_first_open", "platform": "android", "installation_id": install_a,
         "user_id": user_a, "created_at": now.isoformat()},
        {"event_type": "android_first_open", "platform": "android", "installation_id": install_a,
         "user_id": user_a, "created_at": now.isoformat()},
        {"event_type": "android_first_open", "platform": "android", "installation_id": install_b,
         "user_id": user_b, "created_at": now.isoformat()},
        {"event_type": "android_app_open", "platform": "android", "installation_id": install_a,
         "user_id": user_a, "created_at": now.isoformat()},
        {"event_type": "web_session", "platform": "web", "user_id": user_b,
         "created_at": now.isoformat()},
    ]
    metrics = aggregate_events(events, now=now)
    assert metrics["android_installations"] == 2
    assert metrics["android_opens"] == 1
    assert metrics["web_sessions"] == 1
    assert metrics["active_today"] == 2
    assert metrics["active_30d"] == 2


def test_aggregate_excludes_users_outside_active_windows():
    now = datetime(2026, 11, 18, 12, 0, tzinfo=timezone.utc)
    old = now - timedelta(days=40)
    metrics = aggregate_events([{
        "event_type": "web_session", "platform": "web", "user_id": str(uuid4()),
        "created_at": old.isoformat(),
    }], now=now)
    assert metrics["active_today"] == 0
    assert metrics["active_30d"] == 0
    assert metrics["web_sessions"] == 1
    assert len(metrics["daily_active_users"]) == 1


def test_record_event_rejects_invalid_payload_without_database_call():
    class NeverCalled:
        def table(self, _name):
            raise AssertionError("Database should not be called for invalid event data")
    assert record_event(NeverCalled(), "not-a-uuid", "web_session", "web") is False
    assert record_event(NeverCalled(), str(uuid4()), "android_first_open", "web") is False

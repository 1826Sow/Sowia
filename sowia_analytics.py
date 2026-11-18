"""Privacy-minimal SOW IA usage analytics.

Only authenticated user IDs and random installation/session UUIDs are stored.
No prompts, emails, document names, or message content are collected.
"""
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from uuid import UUID

EVENT_TYPES = {"web_session", "android_first_open", "android_app_open"}
PLATFORMS = {"web", "android"}


def record_event(client, user_id, event_type, platform, installation_id=None, session_id=None):
    """Record a validated event using the caller's authenticated Supabase client."""
    if event_type not in EVENT_TYPES or platform not in PLATFORMS:
        return False
    if (event_type == "web_session") != (platform == "web"):
        return False
    try:
        user_uuid = str(UUID(str(user_id)))
        install_uuid = str(UUID(str(installation_id))) if installation_id else None
        session_uuid = str(UUID(str(session_id))) if session_id else None
        if platform == "android" and install_uuid is None:
            return False
        payload = {
            "user_id": user_uuid,
            "event_type": event_type,
            "platform": platform,
            "installation_id": install_uuid,
            "session_id": session_uuid,
        }
        client.table("sowia_analytics_events").insert(payload).execute()
        return True
    except Exception:
        # Analytics must never block login or normal app usage.
        return False


def load_events(admin_client, days=90, limit=10000, now=None):
    """Read a bounded analytics window through the server-side admin client."""
    now = now or datetime.now(timezone.utc)
    since = (now - timedelta(days=max(1, min(int(days), 365)))).isoformat()
    response = (
        admin_client.table("sowia_analytics_events")
        .select("event_type,platform,installation_id,user_id,created_at")
        .gte("created_at", since)
        .order("created_at", desc=True)
        .limit(max(1, min(int(limit), 20000)))
        .execute()
    )
    return list(response.data or [])


def aggregate_events(events, now=None):
    """Return aggregate metrics without exposing individual user identities."""
    now = now or datetime.now(timezone.utc)
    day_start = now - timedelta(days=1)
    month_start = now - timedelta(days=30)
    installs = set()
    active_today = set()
    active_30d = set()
    daily_users = defaultdict(set)
    android_opens = 0
    web_sessions = 0
    valid_rows = 0

    for event in events:
        try:
            created = datetime.fromisoformat(str(event["created_at"]).replace("Z", "+00:00"))
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            created = created.astimezone(timezone.utc)
            event_type = event.get("event_type")
            platform = event.get("platform")
            user_id = str(event.get("user_id") or "")
            valid_rows += 1

            if event_type == "android_first_open" and platform == "android":
                install_id = event.get("installation_id")
                if install_id:
                    installs.add(str(install_id))
            elif event_type == "android_app_open" and platform == "android":
                android_opens += 1
            elif event_type == "web_session" and platform == "web":
                web_sessions += 1

            if user_id and created >= month_start:
                active_30d.add(user_id)
                daily_users[created.date().isoformat()].add(user_id)
            if user_id and created >= day_start:
                active_today.add(user_id)
        except (KeyError, TypeError, ValueError):
            continue

    daily = [
        {"date": day, "users": len(users)}
        for day, users in sorted(daily_users.items())
    ]
    return {
        "android_installations": len(installs),
        "android_opens": android_opens,
        "web_sessions": web_sessions,
        "active_today": len(active_today),
        "active_30d": len(active_30d),
        "daily_active_users": daily,
        "events_loaded": valid_rows,
    }

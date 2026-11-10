import pytest
from business_club import match_profile, validate_profile, validate_request

def profile(name, country="France", offers=(), needs=(), objectives=("export",), **extra):
    return {"company_name": name, "country": country, "sector": "Tech", "description": "Présentation",
            "offers": list(offers), "needs": list(needs), "objectives": list(objectives),
            "website": "", "is_published": True, **extra}

def test_validates_opt_in_profile():
    assert validate_profile(profile("Société A", offers=["logiciel"]))["is_published"] is True

def test_requires_company_and_value_proposition():
    with pytest.raises(ValueError, match="Nom de l'entreprise"):
        validate_profile(profile("", offers=["x"]))
    with pytest.raises(ValueError, match="au moins une offre"):
        validate_profile(profile("A", objectives=[]))

def test_rejects_unsafe_website():
    with pytest.raises(ValueError, match="URL"):
        validate_profile(profile("A", offers=["x"], website="javascript:alert(1)"))

def test_matches_complementary_offers_and_needs():
    result = match_profile(profile("A", offers=["capteurs"], needs=["distribution"]),
                           profile("B", offers=["distribution"], needs=["capteurs"]))
    assert result.score == 65  # 50 complementarity + 15 shared objective
    assert result.recommendation == "Proposer une rencontre exploratoire"

def test_shared_objective_adds_transparent_score():
    result = match_profile(profile("A", offers=["logiciel"], objectives=["export"]),
                           profile("B", needs=["bois"], objectives=["export"], country="Canada"))
    assert result.score == 15
    assert any("deux pays" in item for item in result.evidence)

def test_request_message_is_bounded_and_required():
    assert validate_request("Bonjour, échangeons.") == "Bonjour, échangeons."
    with pytest.raises(ValueError):
        validate_request(" ")

def test_unpublished_flag_must_be_boolean():
    with pytest.raises(ValueError, match="publication"):
        validate_profile(profile("A", offers=["x"], is_published="yes"))


def test_meeting_schedule_normalizes_to_utc():
    from datetime import datetime, timedelta, timezone
    from business_club import validate_meeting_schedule
    future = datetime.now(timezone.utc) + timedelta(days=3)
    result = validate_meeting_schedule(future, "Europe/Paris", 30, "https://meet.example.com/room")
    assert result["timezone"] == "Europe/Paris"
    assert result["duration_minutes"] == 30
    assert result["starts_at"].endswith("+00:00")


def test_meeting_rejects_past_or_invalid_timezone_or_http_url():
    from datetime import datetime, timedelta, timezone
    from business_club import validate_meeting_schedule
    with pytest.raises(ValueError, match="futur"):
        validate_meeting_schedule(datetime.now(timezone.utc) - timedelta(days=1), "UTC", 30)
    with pytest.raises(ValueError, match="Fuseau"):
        validate_meeting_schedule(datetime.now(timezone.utc) + timedelta(days=1), "Mars/Atlantis", 30)
    with pytest.raises(ValueError, match="https"):
        validate_meeting_schedule(datetime.now(timezone.utc) + timedelta(days=1), "UTC", 30, "http://example.com")


def test_meeting_rejects_unsupported_duration():
    from datetime import datetime, timedelta, timezone
    from business_club import validate_meeting_schedule
    with pytest.raises(ValueError, match="durée"):
        validate_meeting_schedule(datetime.now(timezone.utc) + timedelta(days=1), "UTC", 20)


def test_builds_calendar_invite_with_utc_duration_and_video_link():
    from datetime import datetime, timedelta, timezone
    from business_club import build_meeting_ics
    start = datetime.now(timezone.utc) + timedelta(days=2)
    ics = build_meeting_ics({
        "starts_at": start.isoformat(), "duration_minutes": 30,
        "meeting_url": "https://video.example.com/room", "summary": "Partenariat, Europe"
    })
    assert "BEGIN:VCALENDAR" in ics
    assert "SUMMARY:Partenariat\\, Europe" in ics
    assert "URL:https://video.example.com/room" in ics
    assert "DTEND:" in ics


def test_calendar_invite_rejects_invalid_meeting():
    from business_club import build_meeting_ics
    with pytest.raises(ValueError, match="incomplètes"):
        build_meeting_ics({"starts_at": "not-a-date", "duration_minutes": 30})

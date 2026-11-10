"""Tests for weather-to-sector impact screening."""
import pytest

from weather_impact import (
    assess_weather_impacts, normalize_sector_exposure, normalize_weather_event,
)


def event(**updates):
    raw = {
        "event_id": "WX-1", "phenomenon": "flood", "state": "forecast",
        "region": "Rhône-Alpes", "severity": 4, "probability_pct": 75,
        "starts_at": "2026-11-12T08:00:00+01:00",
        "ends_at": "2026-11-12T18:00:00+01:00",
        "source_name": "Official weather service",
        "source_url": "https://weather.example/alerts/1",
        "issued_at": "2026-11-10T08:00:00+01:00",
    }
    raw.update(updates)
    return raw


def exposure(**updates):
    raw = {
        "sector": "Transport", "region": "Rhône-Alpes",
        "vulnerability": 0.8, "direction": "risk_increase",
        "rationale": "Flooding can disrupt roads and rail links",
    }
    raw.update(updates)
    return raw


def test_scores_exposure_and_preserves_forecast_label():
    results = assess_weather_impacts([event()], [exposure()])
    assert len(results) == 1
    assert results[0].screening_score == 48
    assert results[0].state == "forecast"
    assert results[0].probability_pct == 75


def test_observed_event_does_not_require_probability():
    raw = event(state="observed", probability_pct=None)
    result = normalize_weather_event(raw)
    assert result.probability_pct is None
    assert result.state == "observed"


def test_global_exposure_is_explicitly_supported():
    results = assess_weather_impacts([event()], [exposure(region="*")])
    assert len(results) == 1


def test_non_matching_region_is_not_assumed():
    assert assess_weather_impacts([event()], [exposure(region="Brittany")]) == ()


@pytest.mark.parametrize("probability", [None, -1, 101, float("nan"), True])
def test_forecast_requires_valid_probability(probability):
    with pytest.raises(ValueError, match="probabilité"):
        normalize_weather_event(event(probability_pct=probability))


@pytest.mark.parametrize("severity", [0, 6, 2.5, True])
def test_rejects_invalid_severity(severity):
    with pytest.raises(ValueError, match="sévérité"):
        normalize_weather_event(event(severity=severity))


def test_rejects_timezone_naive_dates():
    with pytest.raises(ValueError, match="fuseau horaire"):
        normalize_weather_event(event(starts_at="2026-11-12T08:00:00"))


def test_rejects_non_https_sources():
    with pytest.raises(ValueError, match="HTTPS"):
        normalize_weather_event(event(source_url="http://weather.example/alert"))


def test_rejects_end_before_start():
    with pytest.raises(ValueError, match="précède"):
        normalize_weather_event(event(ends_at="2026-11-11T08:00:00+01:00"))


@pytest.mark.parametrize("vulnerability", [-0.1, 1.1, float("nan"), True])
def test_rejects_invalid_vulnerability(vulnerability):
    with pytest.raises(ValueError, match="vulnérabilité"):
        normalize_sector_exposure(exposure(vulnerability=vulnerability))

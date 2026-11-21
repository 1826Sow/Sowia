import pytest

import weather_tools


def test_weather_intent_and_location_extraction_for_paris():
    assert weather_tools.is_weather_request("Quelle météo fera-t-il demain à Paris ?")
    assert weather_tools.extract_weather_location("Quelle météo fera-t-il demain à Paris ?") == "Paris"
    assert weather_tools.extract_weather_location("Weather in Lyon tomorrow") == "Lyon"


def test_weather_request_without_city_asks_for_location():
    assert weather_tools.answer_weather_request("Quelle est la météo demain ?") == (
        "Bien sûr. Pour quelle ville souhaitez-vous connaître la météo ?"
    )


def test_non_weather_prompt_is_not_intercepted():
    assert weather_tools.answer_weather_request("Explique le changement climatique") is None


def test_get_weather_forecast_uses_geocoding_and_forecast(monkeypatch):
    calls = []

    def fake_request_json(url, params):
        calls.append((url, params))
        if url == weather_tools.GEOCODING_URL:
            return {"results": [{"name": "Paris", "country": "France", "latitude": 48.85, "longitude": 2.35}]}
        return {
            "timezone": "Europe/Paris",
            "current": {
                "temperature_2m": 12, "relative_humidity_2m": 70,
                "apparent_temperature": 10, "weather_code": 2,
                "wind_speed_10m": 8,
            },
            "daily": {
                "time": ["2026-11-21", "2026-11-22"],
                "weather_code": [2, 61],
                "temperature_2m_max": [14, 11],
                "temperature_2m_min": [8, 7],
                "precipitation_probability_max": [10, 80],
            },
        }

    monkeypatch.setattr(weather_tools, "_request_json", fake_request_json)
    result = weather_tools.get_weather_forecast("Paris")
    assert result["location"]["name"] == "Paris"
    assert result["current"]["temperature_2m"] == 12
    assert len(calls) == 2
    assert calls[1][1]["timezone"] == "auto"


def test_weather_report_includes_forecast_and_source():
    report = weather_tools.format_weather_report({
        "location": {"name": "Paris", "country": "France"},
        "current": {"temperature_2m": 12, "apparent_temperature": 10,
                    "relative_humidity_2m": 70, "wind_speed_10m": 8, "weather_code": 2},
        "daily": {"time": ["2026-11-21", "2026-11-22"], "weather_code": [2, 61],
                  "temperature_2m_max": [14, 11], "temperature_2m_min": [8, 7],
                  "precipitation_probability_max": [10, 80]},
        "source": "Open-Meteo",
    })
    assert "Météo — Paris, France" in report
    assert "Demain" in report
    assert "80 %" in report
    assert "Open-Meteo" in report


@pytest.mark.parametrize("days", [0, 8, True, 1.5])
def test_weather_forecast_rejects_invalid_day_count(days):
    with pytest.raises(ValueError, match="1 et 7"):
        weather_tools.get_weather_forecast("Paris", days)


def test_weather_forecast_rejects_unknown_city(monkeypatch):
    monkeypatch.setattr(weather_tools, "_request_json", lambda *args: {"results": []})
    with pytest.raises(LookupError, match="Aucune localité"):
        weather_tools.get_weather_forecast("Ville introuvable")


def test_weather_report_hides_network_details(monkeypatch):
    def fail(*args, **kwargs):
        raise weather_tools.requests.ConnectionError("secret endpoint detail")
    monkeypatch.setattr(weather_tools.requests, "get", fail)
    with pytest.raises(RuntimeError, match="momentanément inaccessible") as exc:
        weather_tools._request_json(weather_tools.GEOCODING_URL, {})
    assert "secret endpoint detail" not in str(exc.value)

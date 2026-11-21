"""Keyless, source-attributed weather lookup for SOW IA using Open-Meteo."""
import re
from datetime import date
import requests

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
WEATHER_CODES = {
    0: "ciel dégagé", 1: "principalement dégagé", 2: "partiellement nuageux",
    3: "couvert", 45: "brouillard", 48: "brouillard givrant",
    51: "bruine légère", 53: "bruine modérée", 55: "bruine dense",
    56: "bruine verglaçante légère", 57: "bruine verglaçante dense",
    61: "pluie faible", 63: "pluie modérée", 65: "forte pluie",
    66: "pluie verglaçante légère", 67: "forte pluie verglaçante",
    71: "faibles chutes de neige", 73: "chutes de neige modérées",
    75: "fortes chutes de neige", 77: "grains de neige",
    80: "averses faibles", 81: "averses modérées", 82: "fortes averses",
    85: "averses de neige faibles", 86: "fortes averses de neige",
    95: "orage", 96: "orage avec grêle faible", 99: "orage avec forte grêle",
}
_TIME_WORDS = r"(?:demain|tomorrow|today|tonight|aujourd'hui|aujourd’hui|ce soir|cette nuit|cette semaine|this week|next week|this weekend|week[- ]?end|la semaine prochaine|sur les?\s+\d+\s+jours)"
_WEATHER_WORDS = r"(?:météo|meteo|temps qu'il fait|prévisions météo|previsions meteo|weather|forecast)"


def is_weather_request(prompt):
    """Detect explicit weather requests without catching general climate discussions."""
    text = str(prompt or "").casefold()
    return bool(re.search(_WEATHER_WORDS, text))


def extract_weather_location(prompt):
    """Extract a likely place name from common French and English weather questions."""
    text = " ".join(str(prompt or "").strip().split())
    if not text:
        return None
    # Prefer the last explicit place preposition (e.g. « demain à Paris »).
    matches = list(re.finditer(
        r"\b(?:à|a|de|du|des|pour|in|for)\b\s+([^,?!;.]+)",
        text, flags=re.IGNORECASE,
    ))
    candidate = matches[-1].group(1).strip() if matches else ""
    if not candidate:
        weather_match = re.search(_WEATHER_WORDS + r"\s+(.+)$", text, flags=re.IGNORECASE)
        candidate = weather_match.group(1).strip() if weather_match else ""
    candidate = re.split(r"\s+" + _TIME_WORDS + r"\b", candidate, maxsplit=1, flags=re.IGNORECASE)[0]
    # Strip sentence punctuation before checking whether the candidate is only a time expression.
    # Weather-word fallback can capture « demain ? » including its question mark.
    candidate_for_time_check = candidate.strip(" .?!,:;()[]")
    if candidate_for_time_check and re.fullmatch(
        _TIME_WORDS, candidate_for_time_check, flags=re.IGNORECASE
    ):
        return None
    candidate = re.sub(r"\b(?:quelle|quel|est|sera|fera|fait-il|fait|à|a|de|du|des|pour|in|for)\b", " ", candidate, flags=re.IGNORECASE)
    candidate = " ".join(candidate.strip(" .?!,:;()[]").split())
    if not candidate or len(candidate) > 100:
        return None
    return candidate


def _request_json(url, params):
    try:
        response = requests.get(url, params=params, timeout=12)
        response.raise_for_status()
        payload = response.json()
    except (requests.Timeout, requests.RequestException) as exc:
        raise RuntimeError("Le service météo est momentanément inaccessible. Réessayez dans quelques instants.") from exc
    except ValueError as exc:
        raise RuntimeError("Le service météo a renvoyé une réponse illisible.") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("La réponse du service météo est invalide.")
    return payload


def get_weather_forecast(location, forecast_days=3):
    """Resolve a city and fetch current conditions plus a short daily forecast."""
    place = " ".join(str(location or "").split())
    if not place or len(place) > 100:
        raise ValueError("Indiquez une ville ou une localité pour consulter la météo.")
    if isinstance(forecast_days, bool) or not isinstance(forecast_days, int) or not 1 <= forecast_days <= 7:
        raise ValueError("La durée des prévisions doit être comprise entre 1 et 7 jours.")
    geo = _request_json(GEOCODING_URL, {"name": place, "count": 1, "language": "fr", "format": "json"})
    results = geo.get("results") or []
    if not results:
        raise LookupError(f"Aucune localité trouvée pour « {place} ». Essayez avec le nom d'une ville plus précis.")
    city = results[0]
    params = {
        "latitude": city["latitude"],
        "longitude": city["longitude"],
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,weather_code,wind_speed_10m",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,sunrise,sunset",
        "forecast_days": forecast_days,
        "timezone": "auto",
    }
    forecast = _request_json(FORECAST_URL, params)
    if not isinstance(forecast.get("current"), dict) or not isinstance(forecast.get("daily"), dict):
        raise RuntimeError("Les prévisions météo reçues sont incomplètes.")
    return {
        "location": {
            "name": city.get("name", place),
            "admin1": city.get("admin1", ""),
            "country": city.get("country", ""),
            "timezone": forecast.get("timezone", ""),
        },
        "current": forecast["current"],
        "daily": forecast["daily"],
        "source": "Open-Meteo",
    }


def format_weather_report(data):
    """Render a concise French report with timestamp and source attribution."""
    place = data["location"]
    current = data["current"]
    daily = data["daily"]
    place_name = ", ".join(part for part in (place.get("name"), place.get("admin1"), place.get("country")) if part)
    code = int(current.get("weather_code", -1))
    lines = [
        f"### Météo — {place_name}",
        f"**Conditions actuelles :** {WEATHER_CODES.get(code, 'conditions non précisées')}.",
        f"**Température :** {current.get('temperature_2m', '—')} °C (ressenti {current.get('apparent_temperature', '—')} °C).",
        f"**Humidité :** {current.get('relative_humidity_2m', '—')} % · **Vent :** {current.get('wind_speed_10m', '—')} km/h.",
        "",
        "**Prévisions :**",
    ]
    dates = daily.get("time", [])
    codes = daily.get("weather_code", [])
    highs = daily.get("temperature_2m_max", [])
    lows = daily.get("temperature_2m_min", [])
    rain = daily.get("precipitation_probability_max", [])
    for index, day in enumerate(dates):
        if index >= len(highs) or index >= len(lows):
            continue
        label = "Aujourd'hui" if index == 0 else ("Demain" if index == 1 else day)
        description = WEATHER_CODES.get(int(codes[index]), "conditions variables") if index < len(codes) else "conditions variables"
        chance = rain[index] if index < len(rain) else "—"
        lines.append(f"- **{label} ({day}) :** {description}, {lows[index]} à {highs[index]} °C, risque de précipitations maximal {chance} %.")
    lines.extend(["", f"Source : {data.get('source', 'Open-Meteo')} · Prévisions consultées à la demande."])
    return "\n".join(lines)


def answer_weather_request(prompt):
    """Return a direct weather answer, or None when the prompt is not about weather."""
    if not is_weather_request(prompt):
        return None
    location = extract_weather_location(prompt)
    if not location:
        return "Bien sûr. Pour quelle ville souhaitez-vous connaître la météo ?"
    return format_weather_report(get_weather_forecast(location))

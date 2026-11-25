"""Automatic detection of questions that need fresh public information."""
import re
import unicodedata

_FRESHNESS_TERMS = (
    "aujourd'hui", "aujourd hui", "actuellement", "en ce moment",
    "a l'instant", "en temps reel", "dernieres nouvelles",
    "derniere actualite", "actualites", "recemment", "cette semaine",
    "ce mois-ci", "cette annee", "maintenant", "cours actuel",
    "prix actuel", "taux actuel", "meteo", "resultats en direct",
    "today", "right now", "currently", "latest", "current", "breaking news",
    "real time", "live results", "current price", "current rate",
    "this week", "this month", "this year", "recent news", "weather",
)
_PATTERNS = (
    re.compile(r"\\b(?:202[5-9]|203\\d)\\b"),
    re.compile(r"\\b(?:latest|current|live|today|now)\\b", re.I),
    re.compile(r"\\b(?:dernier|derniere|derniers|dernieres|actuel|actuelle|actuels|actuelles)\\b", re.I),
)


def _normalize(value):
    normalized = unicodedata.normalize("NFKD", str(value or "").casefold())
    return " ".join("".join(c for c in normalized if not unicodedata.combining(c)).split())


def should_search_web(prompt):
    """Return True only when wording signals a need for fresh information."""
    query = _normalize(prompt)
    if not query:
        return False
    if any(term in query for term in _FRESHNESS_TERMS):
        return True
    return False

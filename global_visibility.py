"""Global visibility planning for SOW IA across startup and technology ecosystems."""
from urllib.parse import urlparse

REGIONS = (
    "Monde entier",
    "Amérique du Nord",
    "Asie de l'Est",
    "Asie du Sud et du Sud-Est",
    "Moyen-Orient",
    "Europe",
    "Afrique",
    "Amérique latine",
)

FOCUS_MARKETS = (
    "États-Unis", "Chine", "Singapour", "Corée du Sud", "Taïwan", "Bali / Indonésie",
    "Inde", "Sénégal", "Suisse", "France", "Dubaï / Émirats arabes unis",
)

AUDIENCES = (
    "Startups et fondateurs",
    "Investisseurs et business angels",
    "Incubateurs et accélérateurs",
    "Salons technologiques et conférences IA",
    "Entreprises et partenaires stratégiques",
    "Programmes publics et écosystèmes émergents",
)


def build_visibility_queries(region, country="", audience="Startups et fondateurs", year=2027):
    region = str(region or "").strip()
    country = str(country or "").strip()
    audience = str(audience or "").strip()
    if region not in REGIONS:
        raise ValueError("Sélectionnez une région valide.")
    if audience not in AUDIENCES:
        raise ValueError("Sélectionnez un public cible valide.")
    if not isinstance(year, int) or year < 2026 or year > 2030:
        raise ValueError("L'année doit être comprise entre 2026 et 2030.")
    location = country or region
    if not location:
        raise ValueError("Indiquez un pays ou une région.")
    core = f"{audience} {location} {year}"
    return [
        f"{core} événements calendrier candidatures exposants startups",
        f"{core} pitch competition startup showcase demo day investisseurs",
        f"{core} incubateurs accélérateurs programmes internationaux partenariats",
    ]


def normalize_visibility_results(items, limit=30):
    if not isinstance(items, list):
        return []
    normalized = []
    seen = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        title = " ".join(str(item.get("title") or "").split())[:240]
        url = str(item.get("url") or "").strip()
        parsed = urlparse(url)
        if not title or parsed.scheme not in {"http", "https"} or not parsed.netloc:
            continue
        key = url.casefold().rstrip("/")
        if key in seen:
            continue
        seen.add(key)
        normalized.append({
            "title": title,
            "url": url[:1000],
            "content": " ".join(str(item.get("content") or item.get("snippet") or "").split())[:1800],
            "domain": parsed.netloc.lower()[:180],
            "status": "À vérifier auprès de l'organisateur",
        })
        if len(normalized) >= max(1, min(int(limit), 50)):
            break
    return normalized

"""Optional web search: Tavily when configured, free DDGS fallback otherwise."""
import requests

from config import TAVILY_API_KEY


def _free_search(cleaned_query, max_results):
    """Search public engines without an API key; results are best-effort."""
    try:
        from ddgs import DDGS
    except ImportError as exc:
        raise RuntimeError(
            "Le moteur de recherche gratuit n'est pas installé. "
            "Le déploiement doit installer la dépendance ddgs."
        ) from exc

    try:
        raw_results = DDGS(timeout=12).text(
            cleaned_query,
            region="fr-fr",
            safesearch="moderate",
            max_results=max_results,
            backend="auto",
        )
    except Exception as exc:
        # Do not expose transport details or request metadata to the interface.
        raise RuntimeError(
            "La recherche Web gratuite est momentanément limitée ou indisponible. "
            "Réessayez dans quelques instants."
        ) from exc

    normalized = []
    for item in raw_results or []:
        if not isinstance(item, dict):
            continue
        url = str(item.get("href") or item.get("url") or "").strip()
        if not url.startswith(("https://", "http://")):
            continue
        normalized.append({
            "title": str(item.get("title") or "Résultat")[:240],
            "url": url,
            "content": str(item.get("body") or item.get("content") or "")[:1600],
        })
    return normalized


def should_search_web(query):
    """Detect explicit browsing requests and questions that require fresh facts.

    Stable explanations and writing tasks stay on the fast AI-only path.
    Explicit requests to search, consult sources or browse are always routed
    through the bounded web pipeline; freshness-sensitive questions are too.
    """
    import re
    import unicodedata

    text = unicodedata.normalize("NFKD", str(query or "").casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    patterns = (
        r"\b(?:aujourd'hui|maintenant|actuellement|en ce moment|en direct|temps reel|a l'instant)\b",
        r"\b(?:dernier(?:e|es|s)?|recent(?:e|es|s)?|actualite(?:s)?|a jour|nouveau(?:elle)?|nouveaute(?:s)?)\b",
        r"\b(?:latest|current|today|right now|live|real[ -]?time|breaking news|newest|recent)\b",
        r"\b(?:prix|tarif(?:s)?|cout|cours|taux|meteo|weather|bourse|stock market|inflation)\b",
        r"\b(?:election(?:s)?|score(?:s)?|resultat(?:s)?|disponibilite|open now|version actuelle|version la plus recente)\b",
        r"\b(?:sur internet|sur le web|recherche web|cherche en ligne|rechercher en ligne|navigation internet|navigue sur internet)\b",
        r"\b(?:cherche|recherche|trouve|consulte|parcours|navigue)\b.{0,70}\b(?:internet|web|en ligne|site(?:s)?|source(?:s)?|lien(?:s)?|url)\b",
        r"\b(?:source(?:s)? fiable(?:s)?|liens? officiels?|site officiel|page officielle)\b",
        r"\b(?:president|premier ministre|ministre|pdg|ceo|directeur general|maire)\b.{0,50}\b(?:actuel|actuelle|en poste|2026|2025)\b",
        r"\b(?:toujours disponible|encore disponible|est sorti|est sortie|a ete annonce|a ete lance)\b",
    )
    return any(re.search(pattern, text) for pattern in patterns)


def search_web(query, max_results=5):
    """Search the web with Tavily or a no-key public-search fallback."""
    cleaned_query = str(query or "").strip()
    if not cleaned_query:
        raise ValueError("Saisissez une recherche avant de lancer la recherche Web.")
    if len(cleaned_query) > 500:
        raise ValueError("La recherche est trop longue (500 caractères maximum).")

    if isinstance(max_results, bool) or not isinstance(max_results, int):
        raise ValueError("Le nombre de résultats doit être un entier entre 1 et 10.")
    if not 1 <= max_results <= 10:
        raise ValueError("Le nombre de résultats doit être compris entre 1 et 10.")

    # Tavily remains available when the owner has configured a key.
    # Otherwise use public search engines without requiring a paid API account.
    if not TAVILY_API_KEY:
        return _free_search(cleaned_query, max_results)

    try:
        response = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": TAVILY_API_KEY,
                "query": cleaned_query,
                "max_results": max_results,
            },
            timeout=25,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.Timeout as exc:
        raise RuntimeError("La recherche Web a dépassé le délai autorisé. Réessayez plus tard.") from exc
    except requests.RequestException as exc:
        raise RuntimeError("Le service de recherche Web est momentanément indisponible.") from exc
    except ValueError as exc:
        raise RuntimeError("Le service de recherche Web a renvoyé une réponse illisible.") from exc

    results = payload.get("results", []) if isinstance(payload, dict) else []
    return results if isinstance(results, list) else []

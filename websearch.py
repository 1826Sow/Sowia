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

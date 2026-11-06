"""Optional web search via Tavily with bounded input and output."""
import requests

from config import TAVILY_API_KEY

MAX_QUERY_CHARS = 500
MAX_RESULTS = 10


def search_web(query, max_results=5):
    """Search the web with bounded query size, result count and network time."""
    if not TAVILY_API_KEY:
        raise RuntimeError(
            "La recherche Web nécessite une clé TAVILY_API_KEY dans les secrets."
        )
    if not isinstance(query, str) or not query.strip():
        raise ValueError("Saisissez une recherche avant de continuer.")
    query = query.strip()
    if len(query) > MAX_QUERY_CHARS:
        raise ValueError("La recherche est trop longue (500 caractères maximum).")
    if isinstance(max_results, bool) or not isinstance(max_results, int):
        raise ValueError("Le nombre de résultats demandé est invalide.")
    if not 1 <= max_results <= MAX_RESULTS:
        raise ValueError("Le nombre de résultats doit être compris entre 1 et 10.")

    response = requests.post(
        "https://api.tavily.com/search",
        json={
            "api_key": TAVILY_API_KEY,
            "query": query,
            "max_results": max_results,
        },
        timeout=(5, 20),
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError("Réponse de recherche invalide.")
    results = payload.get("results", [])
    if not isinstance(results, list):
        raise RuntimeError("Format des résultats de recherche invalide.")
    return results[:max_results]

"""Optional web search via Tavily."""
import requests

from config import TAVILY_API_KEY


def search_web(query, max_results=5):
    """Search the web with clear configuration and input errors."""
    if not TAVILY_API_KEY:
        raise RuntimeError(
            "La recherche Web nécessite TAVILY_API_KEY dans les secrets Streamlit "
            "ou dans les variables d'environnement du serveur. Ne partagez jamais cette clé."
        )

    cleaned_query = str(query or "").strip()
    if not cleaned_query:
        raise ValueError("Saisissez une recherche avant de lancer la recherche Web.")
    if len(cleaned_query) > 500:
        raise ValueError("La recherche est trop longue (500 caractères maximum).")

    if isinstance(max_results, bool) or not isinstance(max_results, int):
        raise ValueError("Le nombre de résultats doit être un entier entre 1 et 10.")
    if not 1 <= max_results <= 10:
        raise ValueError("Le nombre de résultats doit être compris entre 1 et 10.")

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

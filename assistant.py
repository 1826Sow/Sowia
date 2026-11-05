"""LLM assistant adapter with a transparent no-credit fallback."""
from openai import OpenAI, AuthenticationError, RateLimitError
from config import API_KEY, BASE_URL, MODEL, SYSTEM_PROMPT


def _offline_reply(messages):
    """Return honest, limited help when the paid API is unavailable."""
    prompt = ""
    for item in reversed(messages or []):
        if item.get("role") == "user":
            prompt = str(item.get("content", "")).strip()
            break

    lowered = prompt.lower()
    if any(word in lowered for word in ("429", "crédit", "credits", "quota", "facturation")):
        return (
            "SOW IA fonctionne en mode de secours : le quota du fournisseur IA est épuisé "
            "(erreur 429). Aucune réponse générative OpenAI ne peut être produite "
            "tant que le quota n'est pas rétabli. Vous pouvez continuer à utiliser "
            "les fonctions locales de l'application, notamment l'historique, la "
            "mémoire et l'importation de PDF. Je peux aussi vous guider dans les "
            "réglages, étape par étape, sans vous demander de communiquer votre clé API."
        )
    if any(word in lowered for word in ("pdf", "document", "fichier")):
        return (
            "Le service IA est temporairement indisponible faute de quota. "
            "Vous pouvez néanmoins ouvrir « Analyse PDF » pour importer un PDF "
            "et extraire son texte. Vous pouvez aussi créer et télécharger un PDF "
            "depuis la rubrique « Créer un PDF », sans consommer de crédit OpenAI."
        )
    if any(word in lowered for word in ("mémoire", "memoire", "historique", "sauvegarder")):
        return (
            "Même sans crédits OpenAI, les fonctions locales de mémoire et "
            "d'historique de SOW IA restent accessibles dans leurs rubriques, "
            "sous réserve que le stockage de l'application soit disponible."
        )
    return (
        "Le mode de secours de SOW IA est actif. Le quota du service OpenAI est "
        "épuisé : je ne peux donc pas générer une véritable réponse IA pour le moment. "
        "Les rubriques locales de l'application restent utilisables. Vous pouvez "
        "me demander de l'aide sur les réglages, la mémoire, l'historique ou les "
        "documents ; je vous indiquerai ce qui fonctionne sans crédits."
    )


def answer(messages, memories=None):
    if not API_KEY:
        raise RuntimeError(
            "Aucune clé API IA n'est configurée. Ajoutez GROQ_API_KEY ou OPENAI_API_KEY dans Streamlit > Secrets. Ouvrez "
            "Paramètres > Secrets et vérifiez le nom exact OPENAI_API_KEY. "
            "Ne partagez jamais votre clé API."
        )

    system_prompt = SYSTEM_PROMPT
    saved_memories = [item.strip() for item in (memories or []) if item and item.strip()]
    if saved_memories:
        memory_context = "\n".join(f"- {item}" for item in saved_memories)
        system_prompt += (
            "\n\nInformations mémorisées par l'utilisateur (à utiliser uniquement "
            "si elles sont pertinentes) :\n" + memory_context
        )

    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": system_prompt}, *messages],
            temperature=0.4,
        )
    except AuthenticationError as exc:
        raise RuntimeError(
            "Le fournisseur IA refuse la clé API (erreur 401). La connexion de SOW IA fonctionne, "
            "mais la clé enregistrée n'est pas acceptée par OpenAI. Dans Streamlit > "
            "Paramètres > Secrets, vérifiez que OPENAI_API_KEY contient une clé API "
            "active copiée depuis le tableau de bord de votre fournisseur, sans texte "
            "supplémentaire. Vérifiez aussi que OPENAI_BASE_URL n'est pas renseigné "
            "si vous utilisez l'API officielle OpenAI. Ne communiquez jamais votre clé."
        ) from exc
    except RateLimitError:
        return _offline_reply(messages)

    return response.choices[0].message.content or ""

"""LLM assistant adapter using the OpenAI API."""
from openai import OpenAI, AuthenticationError
from config import API_KEY, BASE_URL, MODEL, SYSTEM_PROMPT


def answer(messages, memories=None):
    if not API_KEY:
        raise RuntimeError(
            "La clé OPENAI_API_KEY est absente. Dans Streamlit, ouvrez "
            "Paramètres > Secrets et vérifiez le nom exact OPENAI_API_KEY."
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
            "OpenAI refuse la clé API (erreur 401). La connexion de SOW IA fonctionne, "
            "mais la clé enregistrée n'est pas acceptée par OpenAI. Dans Streamlit > "
            "Paramètres > Secrets, vérifiez que OPENAI_API_KEY contient une clé API "
            "active copiée depuis https://platform.openai.com/api-keys, sans texte "
            "supplémentaire. Vérifiez aussi que OPENAI_BASE_URL n'est pas renseigné "
            "si vous utilisez l'API officielle OpenAI. Ne communiquez jamais votre clé."
        ) from exc

    return response.choices[0].message.content or ""

"""LLM assistant adapter using an OpenAI-compatible API."""
from openai import OpenAI
from config import API_KEY, BASE_URL, MODEL, SYSTEM_PROMPT


def answer(messages, memories=None):
    if not API_KEY:
        raise RuntimeError(
            "La clé OPENAI_API_KEY n'est pas configurée. Ajoutez-la dans le fichier .env."
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
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": system_prompt}, *messages],
        temperature=0.4,
    )
    return response.choices[0].message.content or ""

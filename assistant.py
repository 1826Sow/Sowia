"""LLM assistant adapter using an OpenAI-compatible API."""
from openai import OpenAI
from config import API_KEY,BASE_URL,MODEL,SYSTEM_PROMPT
def answer(messages):
    if not API_KEY: raise RuntimeError("La clé OPENAI_API_KEY n'est pas configurée. Ajoutez-la dans le fichier .env.")
    client=OpenAI(api_key=API_KEY,base_url=BASE_URL)
    response=client.chat.completions.create(model=MODEL,messages=[{"role":"system","content":SYSTEM_PROMPT},*messages],temperature=0.4)
    return response.choices[0].message.content or ""

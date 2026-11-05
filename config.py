"""Central configuration for SOW IA."""
from settings import get_setting

APP_NAME = "SOW IA"


def _clean_secret(value):
    """Normalize a secret pasted into Streamlit Secrets or an environment variable."""
    if value is None:
        return ""
    return str(value).strip().strip('"').strip("'")


# Prefer Groq when configured; otherwise keep the existing OpenAI setup.
GROQ_API_KEY = _clean_secret(get_setting("GROQ_API_KEY", ""))
OPENAI_API_KEY = _clean_secret(get_setting("OPENAI_API_KEY", ""))
API_KEY = GROQ_API_KEY or OPENAI_API_KEY
DEFAULT_MODEL = "openai/gpt-oss-20b" if GROQ_API_KEY else "gpt-4o-mini"
MODEL = _clean_secret(get_setting("GROQ_MODEL" if GROQ_API_KEY else "OPENAI_MODEL", DEFAULT_MODEL)) or DEFAULT_MODEL
DEFAULT_BASE_URL = "https://api.groq.com/openai/v1" if GROQ_API_KEY else ""
BASE_URL = _clean_secret(get_setting("OPENAI_BASE_URL", DEFAULT_BASE_URL)) or None
TAVILY_API_KEY = _clean_secret(get_setting("TAVILY_API_KEY", ""))
SYSTEM_PROMPT = (
    "Tu es SOW IA, un assistant intelligent, clair et fiable. "
    "Réponds dans la langue de l'utilisateur. N'invente jamais de faits, "
    "de sources ou de résultats. Signale les incertitudes."
)

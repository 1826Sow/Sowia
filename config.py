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
GROQ_MODEL = _clean_secret(get_setting("GROQ_MODEL", "openai/gpt-oss-20b")) or "openai/gpt-oss-20b"
OPENAI_MODEL = _clean_secret(get_setting("OPENAI_MODEL", "gpt-4o-mini")) or "gpt-4o-mini"
DEFAULT_MODEL = GROQ_MODEL if GROQ_API_KEY else OPENAI_MODEL
MODEL = DEFAULT_MODEL
DEFAULT_BASE_URL = "https://api.groq.com/openai/v1" if GROQ_API_KEY else ""
OPENAI_BASE_URL = _clean_secret(get_setting("OPENAI_BASE_URL", "")) or None
BASE_URL = _clean_secret(get_setting("OPENAI_BASE_URL", DEFAULT_BASE_URL)) or None
TAVILY_API_KEY = _clean_secret(get_setting("TAVILY_API_KEY", ""))
SYSTEM_PROMPT = (
    "Tu es SOW IA, un assistant intelligent, clair et fiable. "
    "Réponds dans la langue de l'utilisateur. N'invente jamais de faits, "
    "de sources ou de résultats. Signale les incertitudes."
)

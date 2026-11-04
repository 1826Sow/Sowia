"""Central configuration for SOW IA."""
from settings import get_setting

APP_NAME = "SOW IA"


def _clean_secret(value):
    """Normalize a secret pasted into Streamlit Secrets or an environment variable."""
    if value is None:
        return ""
    return str(value).strip().strip('"').strip("'")


MODEL = _clean_secret(get_setting("OPENAI_MODEL", "gpt-4o-mini")) or "gpt-4o-mini"
API_KEY = _clean_secret(get_setting("OPENAI_API_KEY", ""))
BASE_URL = _clean_secret(get_setting("OPENAI_BASE_URL", "")) or None
TAVILY_API_KEY = _clean_secret(get_setting("TAVILY_API_KEY", ""))
SYSTEM_PROMPT = (
    "Tu es SOW IA, un assistant intelligent, clair et fiable. "
    "Réponds dans la langue de l'utilisateur. N'invente jamais de faits, "
    "de sources ou de résultats. Signale les incertitudes."
)

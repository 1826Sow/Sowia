"""Central configuration for SOW IA."""
import os
from dotenv import load_dotenv
load_dotenv()
APP_NAME="SOW IA"
MODEL=os.getenv("OPENAI_MODEL","gpt-4o-mini")
API_KEY=os.getenv("OPENAI_API_KEY","")
BASE_URL=os.getenv("OPENAI_BASE_URL") or None
TAVILY_API_KEY=os.getenv("TAVILY_API_KEY","")
SYSTEM_PROMPT="Tu es SOW IA, un assistant intelligent, clair et fiable. Réponds dans la langue de l'utilisateur. N'invente jamais de faits, de sources ou de résultats. Signale les incertitudes."

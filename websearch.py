"""Optional web search via Tavily."""
from config import TAVILY_API_KEY
import requests
def search_web(query,max_results=5):
    if not TAVILY_API_KEY: raise RuntimeError("La recherche Web nécessite une clé TAVILY_API_KEY dans le fichier .env.")
    response=requests.post("https://api.tavily.com/search",json={"api_key":TAVILY_API_KEY,"query":query,"max_results":max_results},timeout=25)
    response.raise_for_status(); return response.json().get("results",[])

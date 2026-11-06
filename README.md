# SOW IA

Application web d'intelligence artificielle construite avec Streamlit.

## Socle actuel

- Interface Streamlit SOW IA
- Assistant conversationnel via API compatible OpenAI
- Historique local SQLite pour le développement
- Authentification GitHub via Supabase Auth (PKCE)
- Historique et mémoire cloud isolés par utilisateur avec politiques RLS
- Extraction de texte depuis les PDF
- Recherche web optionnelle via Tavily
- Stockage PDF privé Supabase avec politiques par utilisateur
- Configuration Docker et tests automatisés

## Déploiement public (Streamlit Community Cloud)

1. Connecter le dépôt GitHub `1826Sow/Sowia` à Streamlit Community Cloud.
2. Choisir la branche `main` et le fichier principal `app.py`.
3. Dans Supabase > SQL Editor, ouvrir `supabase/schema.sql` depuis ce dépôt et exécuter tout le script. Il crée les tables, active les règles RLS et configure le bucket PDF privé avec ses règles d'accès.
4. Dans les paramètres **Secrets** de l'application Streamlit, renseigner les variables nécessaires.
5. Dans Supabase > Authentication > URL Configuration, ajouter l'URL HTTPS de l'application comme **Site URL** et dans **Redirect URLs**.
6. Dans Supabase > Authentication > Providers, activer GitHub et vérifier les identifiants OAuth GitHub.
7. Tester la connexion GitHub, l'enregistrement d'une conversation, la mémoire, les documents privés et la déconnexion avec deux comptes de test distincts.

### Secrets requis

**Option recommandée : Groq (quota gratuit limité).**

```toml
GROQ_API_KEY = "..."
GROQ_MODEL = "openai/gpt-oss-20b"
SUPABASE_URL = "https://VOTRE-PROJET.supabase.co"
SUPABASE_ANON_KEY = "VOTRE_CLE_ANON"
SOWIA_PUBLIC_URL = "https://VOTRE-APPLICATION.streamlit.app"
SOWIA_REQUIRE_AUTH = "true"
```

SOW IA sélectionne automatiquement Groq lorsqu'une variable `GROQ_API_KEY` est présente. Le forfait gratuit est soumis à des limites d'utilisation ; en cas de dépassement, le service peut temporairement refuser les requêtes.

**Alternative : OpenAI**

```toml
OPENAI_API_KEY = "..."
OPENAI_MODEL = "gpt-4o-mini"
SUPABASE_URL = "https://VOTRE-PROJET.supabase.co"
SUPABASE_ANON_KEY = "VOTRE_CLE_ANON"
SOWIA_PUBLIC_URL = "https://VOTRE-APPLICATION.streamlit.app"
SOWIA_REQUIRE_AUTH = "true"
```

Ajouter `TAVILY_API_KEY` seulement si la recherche web est utilisée. Ne jamais ajouter la clé Supabase `service_role` dans le navigateur ou sur GitHub. Si les fonctions Premium sont ultérieurement activées, la clé de service doit rester exclusivement dans les secrets privés du serveur Streamlit.

Le mode public doit impérativement conserver `SOWIA_REQUIRE_AUTH = "true"`. Si Supabase n'est pas configuré, l'application doit rester fermée plutôt que d'ouvrir un accès non authentifié. Le mode local sans authentification est réservé au développement sur une machine privée.

## Installation locale

1. Installer Python 3.10 ou supérieur.
2. Installer les dépendances : `pip install -r requirements.txt`.
3. Copier `.env.example` vers `.env` et renseigner les clés nécessaires.
4. Démarrer : `streamlit run app.py`.

En local uniquement, `SOWIA_REQUIRE_AUTH=false` peut être utilisé pour les tests sans authentification. Ne jamais utiliser ce réglage sur une instance publique.

## Vérification

```bash
python -m compileall -q .
pytest -q
```

Une action GitHub exécute ces contrôles automatiquement sur les modifications.

## État de mise en production

Le dépôt contient l'intégration Supabase et les tests automatisés. La configuration effective des secrets de l'hébergeur, les URL OAuth autorisées et les tests de bout en bout sur l'URL publique doivent encore être vérifiés. Le paiement PayPal reste volontairement désactivé jusqu'à sa mise en service explicite par le propriétaire.

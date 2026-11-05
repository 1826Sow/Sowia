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
- Configuration Docker et tests automatisés

## Déploiement public (Streamlit Community Cloud)

1. Connecter le dépôt GitHub `1826Sow/Sowia` à Streamlit Community Cloud.
2. Choisir la branche `main` et le fichier principal `app.py`.
3. Dans Supabase > SQL Editor, ouvrir `supabase_schema.sql` depuis ce dépôt, exécuter tout le script, puis vérifier que les tables `sowia_memory_items` et `sowia_messages` existent.\n4. Dans les paramètres **Secrets** de l'application Streamlit, renseigner les variables ci-dessous.
5. Dans Supabase > Authentication > URL Configuration, ajouter l'URL HTTPS de l'application comme **Site URL** et dans **Redirect URLs**.
6. Dans Supabase > Authentication > Providers, activer GitHub et vérifier les identifiants OAuth GitHub.
7. Tester la connexion GitHub, l'enregistrement d'une conversation, la mémoire et la déconnexion avec un compte de test.

### Secrets requis

**Option recommandée sans frais obligatoires : Groq (quota gratuit limité).** Créez une clé API dans le tableau de bord Groq, puis ajoutez-la dans les Secrets Streamlit :

```toml
GROQ_API_KEY = "..."
GROQ_MODEL = "openai/gpt-oss-20b"
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

Ajouter aussi `TAVILY_API_KEY` seulement si la recherche web est utilisée. Ne jamais ajouter la clé Supabase `service_role` dans Streamlit, le navigateur ou GitHub. Utiliser uniquement la clé publique anon/publishable avec les politiques RLS activées.

Le mode public doit impérativement conserver `SOWIA_REQUIRE_AUTH=true`. Si Supabase n'est pas configuré, l'application doit rester fermée plutôt que d'ouvrir un accès non authentifié.

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

Le dépôt contient l'intégration Supabase et les tests de sécurité associés. Le déploiement effectif, les secrets de l'hébergeur, les URL OAuth autorisées et les tests de bout en bout sur l'URL publique restent à effectuer. Ne pas annoncer l'application comme publiée avant ces vérifications.

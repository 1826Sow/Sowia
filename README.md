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
3. **Ne pas exécuter de script SQL sur le projet Supabase actuellement utilisé par SOW IA.** Avant toute migration, créer un projet Supabase de test distinct et suivre intégralement `SUPABASE_ISOLATED_VALIDATION.md`, en commençant par les précontrôles en lecture seule.
4. Dans ce projet isolé uniquement, suivre l'ordre documenté : `supabase/schema.sql` (schéma de base), puis `supabase_optional_features.sql` (Storage privé et politique Premium).
5. Le fichier racine historique `supabase_schema.sql` est obsolète pour cette procédure : **ne pas l'exécuter**. Il n'est pas interchangeable avec `supabase/schema.sql` et accorde des privilèges de séquence plus larges.
6. Dans les paramètres **Secrets** de Streamlit, renseigner les variables ci-dessous. Pour une instance publique, `SOWIA_REQUIRE_AUTH` doit être explicitement réglé sur `true`.
7. Dans Supabase > Authentication > URL Configuration, ajouter l'URL HTTPS de l'application comme **Site URL** et dans **Redirect URLs**.
8. Dans Supabase > Authentication > Providers, activer GitHub et vérifier les identifiants OAuth GitHub.
9. Après validation isolée et configuration autorisée, tester la connexion GitHub, l'enregistrement d'une conversation, la mémoire et la déconnexion avec deux comptes de test distincts.

### Secrets requis

**Option recommandée sans frais obligatoires : Groq (quota gratuit limité).** Créez une clé API dans le tableau de bord Groq, puis ajoutez-la dans les Secrets Streamlit :

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

Le dépôt contient l'intégration Supabase et les tests de sécurité associés. Le déploiement effectif, les secrets de l'hébergeur, les URL OAuth autorisées et les tests de bout en bout sur l'URL publique restent à effectuer. Aucun SQL de migration ne doit être exécuté sur la base de production avant revue spécifique et validation isolée. Ne pas annoncer l'application comme publiée avant ces vérifications.

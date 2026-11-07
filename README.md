# SOW IA

Application web d'intelligence artificielle construite avec Streamlit.

## Fonctionnalités

- Assistant conversationnel via API compatible OpenAI
- Authentification Supabase par adresse e-mail et mot de passe (PKCE)
- Création de compte, confirmation d'adresse e-mail et récupération du mot de passe
- Historique et mémoire cloud isolés par utilisateur avec politiques RLS
- Extraction et analyse de texte depuis les PDF
- Création et téléchargement de PDF
- Recherche web optionnelle via Tavily
- Tests automatisés et contrôles GitHub Actions

## Configuration de l'authentification publique

La configuration doit être vérifiée avant de déployer la branche contenant la connexion e-mail.

### 1. Secrets Streamlit

Dans les paramètres **Secrets** de l'application Streamlit, renseigner les valeurs réelles (ne jamais les publier sur GitHub) :

```toml
SUPABASE_URL = "https://VOTRE-PROJET.supabase.co"
SUPABASE_ANON_KEY = "VOTRE_CLE_PUBLIQUE_ANON"
SOWIA_PUBLIC_URL = "https://VOTRE-APPLICATION.streamlit.app"
SOWIA_REQUIRE_AUTH = "true"
```

Pour activer les réponses IA, ajouter un fournisseur configuré. Groq peut proposer un quota gratuit limité :

```toml
GROQ_API_KEY = "..."
GROQ_MODEL = "openai/gpt-oss-20b"
```

Ou utiliser une clé OpenAI si elle est disponible. Ajouter `TAVILY_API_KEY` uniquement si la recherche web doit être activée.

Ne jamais placer la clé Supabase `service_role` dans le navigateur, dans GitHub ou dans les secrets publics. L'application destinée au public doit rester en mode protégé avec `SOWIA_REQUIRE_AUTH = "true"`.

### 2. Réglages Supabase Auth

Dans Supabase, ouvrir **Authentication** :

1. Dans **Providers**, vérifier que le fournisseur **Email** est activé.
2. Dans **URL Configuration**, définir **Site URL** avec l'URL HTTPS exacte de l'application Streamlit.
3. Dans **Redirect URLs**, autoriser cette même URL HTTPS exacte. Ne pas ajouter de joker inutile.
4. Vérifier que la confirmation d'adresse e-mail est configurée et que les e-mails de confirmation et de récupération utilisent les liens Supabase standards, qui redirigent vers l'URL autorisée.
5. Vérifier que l'envoi d'e-mails fonctionne. Pour un usage public, prévoir un service SMTP fiable si les limites d'envoi par défaut sont insuffisantes.

L'application utilise `SOWIA_PUBLIC_URL` comme destination des liens de confirmation et de récupération. Les liens de récupération ajoutent le paramètre `sowia_recovery=1` pour ouvrir l'écran de définition du nouveau mot de passe.

### 3. Données et sécurité

Dans Supabase **SQL Editor**, exécuter le script `supabase_schema.sql` du dépôt si ce n'est pas déjà fait. Il crée les tables `sowia_memory_items` et `sowia_messages`, active leurs politiques RLS, crée le bucket privé `sowia-private-documents` et limite la lecture, l'envoi et la suppression des PDF au dossier correspondant à l'identifiant de chaque utilisateur.

Le script peut être réexécuté pour remettre à jour les politiques qu'il gère. Après exécution, tester avec deux comptes distincts que chaque compte ne peut ni lister, ni télécharger, ni supprimer les documents de l'autre.

## Déploiement Streamlit

Après validation et fusion de la branche de préparation :

1. Connecter le dépôt GitHub `1826Sow/Sowia` à Streamlit Community Cloud.
2. Choisir la branche `main` et le fichier principal `app.py`.
3. Vérifier les secrets Streamlit sans les copier dans GitHub.
4. Redémarrer l'application et tester avec un compte de test.

Ne pas fusionner ni déployer la nouvelle authentification avant la vérification des réglages Supabase et un test réel du parcours complet.

## Installation locale

1. Installer Python 3.10 ou supérieur.
2. Installer les dépendances : `pip install -r requirements.txt`.
3. Copier `.env.example` vers `.env` et renseigner les clés nécessaires.
4. Démarrer : `streamlit run app.py`.

En local uniquement, `SOWIA_REQUIRE_AUTH=false` peut être utilisé pour les tests sans authentification. Ne jamais utiliser ce réglage sur une instance publique.

## Vérification automatisée

```bash
python -m compileall -q .
pytest -q
```

Une action GitHub exécute ces contrôles automatiquement sur les modifications.

## État de mise en production

La connexion e-mail est préparée sur une branche séparée. Les réglages du projet Supabase, l'envoi réel des e-mails, les tests de bout en bout et la validation du stockage privé restent à vérifier avant mise en production. Les paiements restent désactivés tant que leur activation n'a pas été décidée séparément.

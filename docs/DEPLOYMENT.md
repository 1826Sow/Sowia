# Préparer l'hébergement et la connexion GitHub de SOW IA

Le dépôt est préparé pour un déploiement Streamlit avec Supabase Auth (connexion GitHub) et une base PostgreSQL protégée par Row Level Security (RLS).

## 1. Hébergement de l'application

Option retenue pour le premier déploiement : **Streamlit Community Cloud** (connexion au dépôt GitHub, déploiement de `app.py`). Il faudra choisir le dépôt `1826Sow/Sowia`, la branche `main` et le fichier `app.py`. L'adresse HTTPS sera fournie par la plateforme après le déploiement.

Ne pas publier l'application actuelle à plusieurs utilisateurs avant l'intégration complète de l'authentification et du stockage cloud.

## 2. Base de données et authentification

Créer un projet Supabase, puis exécuter le fichier `supabase/schema.sql` dans le SQL Editor. Ce schéma crée les tables de messages et de mémoire avec des politiques RLS qui interdisent l'accès aux données d'un autre compte.

Dans Supabase, relever l'URL du projet et la clé publishable/anon. Les ajouter aux secrets de l'hébergeur sous les noms :
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SOWIA_PUBLIC_URL` (URL HTTPS de l'application après déploiement)

Ne jamais utiliser la clé `service_role` dans l'application Streamlit.

## 3. Connexion GitHub dans Supabase

Dans Supabase : Authentication → Sign In / Providers → GitHub. Activer GitHub. Supabase affiche une URL de callback de la forme `https://<project-ref>.supabase.co/auth/v1/callback`.

Créer ensuite une GitHub OAuth App :
- Homepage URL : URL HTTPS publique de SOW IA.
- Authorization callback URL : URL de callback affichée par Supabase.

Copier le Client ID et le Client Secret dans les réglages du fournisseur GitHub de Supabase. Ajouter l'URL publique de SOW IA dans la liste des Redirect URLs autorisées de Supabase.

## 4. Variables d'environnement

Modèle de secrets (à saisir dans l'interface de l'hébergeur, pas dans Git) :

```toml
SUPABASE_URL = "https://<project-ref>.supabase.co"
SUPABASE_ANON_KEY = "<clé-publishable-ou-anon>"
SOWIA_PUBLIC_URL = "https://<adresse-deploiement>"
```

Le Client ID et le Client Secret GitHub sont enregistrés uniquement dans les paramètres du fournisseur GitHub de Supabase, jamais dans les secrets de l'application si Supabase gère le callback OAuth.

## 5. État de préparation

Cette étape ajoute les fondations OAuth et le schéma RLS, mais ne signifie pas que le bouton de connexion est déjà intégré à toutes les pages de l'application. Le parcours complet doit encore être intégré à l'interface, testé sur l'URL HTTPS réelle, et l'historique/mémoire SQLite existants ne doivent pas être importés automatiquement. Ils restent inchangés jusqu'à une migration contrôlée.

Aucune clé, aucun mot de passe et aucun secret n'est requis dans ce dépôt.

# Configuration OAuth GitHub — SOW IA

Ce guide concerne la connexion GitHub via **Supabase Auth (PKCE)** utilisée par SOW IA.

## 1. Adresse publique de SOW IA

Dans les secrets Streamlit, définir :

```toml
SUPABASE_URL = "https://VOTRE-PROJET.supabase.co"
SUPABASE_ANON_KEY = "VOTRE_CLE_ANON"
SOWIA_PUBLIC_URL = "https://VOTRE-APPLICATION.streamlit.app"
SOWIA_REQUIRE_AUTH = "true"
```

Utiliser l'URL HTTPS réelle de l'application Streamlit, sans inventer de domaine ni ajouter de chemin inutile. La clé doit être la clé publique anon/publishable. Ne jamais utiliser `service_role`.

## 2. Autoriser le retour dans Supabase

Dans **Supabase > Authentication > URL Configuration** :

- définir **Site URL** sur l'URL HTTPS exacte de l'application SOW IA ;
- ajouter cette même URL exacte à **Redirect URLs** ;
- éviter les jokers trop larges et les domaines non maîtrisés.

SOW IA transmet `SOWIA_PUBLIC_URL` comme `redirect_to`. Supabase doit autoriser cette adresse dans sa liste de redirections. Le contrôle du code confirme qu'il s'agit d'une URL HTTPS valide, mais c'est la liste d'autorisation Supabase qui décide si la destination est permise.

## 3. Configurer GitHub comme fournisseur

Dans **Supabase > Authentication > Providers > GitHub** :

- activer le fournisseur GitHub ;
- renseigner le Client ID et le Client Secret de l'application OAuth GitHub ;
- copier l'URL de rappel/callback affichée par Supabase.

Dans les paramètres de l'application OAuth GitHub, coller **l'URL de callback fournie par Supabase** dans le champ *Authorization callback URL*. Ce n'est pas l'URL publique Streamlit : le retour final vers Streamlit est géré par Supabase après l'authentification.

Ne jamais placer le Client Secret GitHub dans le dépôt, dans le code source ou dans un message public.

## 4. Contrôles après configuration

Effectuer les tests avec un compte de test :

1. ouvrir l'URL publique SOW IA ;
2. vérifier que l'accès demande une connexion ;
3. lancer « Continuer avec GitHub » et terminer l'autorisation ;
4. vérifier que l'application revient sur le domaine Streamlit HTTPS attendu ;
5. enregistrer une mémoire et un message, actualiser la page et vérifier leur persistance ;
6. se déconnecter et vérifier que l'écran de connexion réapparaît ;
7. si possible, refaire le test avec un second compte et confirmer qu'il ne voit ni la mémoire, ni les messages, ni les documents du premier compte.

## 5. Ce qui reste à vérifier

Les tests automatisés du dépôt utilisent des clients simulés : ils ne prouvent pas que le fournisseur GitHub, les secrets Streamlit, les URL autorisées ou les politiques RLS sont correctement configurés dans le projet Supabase réel.

Après les migrations SQL, exécuter `supabase/verify_security.sql` dans le bon projet Supabase. Une validation complète de l'isolation nécessite aussi des essais avec deux comptes distincts.

Ne jamais désactiver RLS pour faire disparaître une erreur et ne jamais publier une clé `service_role`.

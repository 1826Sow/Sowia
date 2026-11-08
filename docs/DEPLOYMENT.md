# Préparer l'hébergement et la connexion GitHub de SOW IA

Le dépôt est préparé pour un déploiement Streamlit avec Supabase Auth (connexion GitHub) et une base PostgreSQL protégée par Row Level Security (RLS).

## 1. Hébergement de l'application

Option retenue pour le premier déploiement : **Streamlit Community Cloud** (connexion au dépôt GitHub, déploiement de `app.py`). Il faudra choisir le dépôt `1826Sow/Sowia`, la branche `main` et le fichier `app.py`. L'adresse HTTPS sera fournie par la plateforme après le déploiement.

Le parcours de connexion et les accès à la mémoire/historique cloud sont maintenant raccordés dans l'interface. Pour tout hébergement public, définir impérativement `SOWIA_REQUIRE_AUTH=true` afin de fermer l'accès tant que Supabase n'est pas configuré. Ne pas ouvrir au public avant les essais réels OAuth et RLS.

## 2. Base de données et authentification

Créer un projet Supabase, puis exécuter le fichier `supabase/schema.sql` dans le SQL Editor. Ce schéma crée les tables de messages et de mémoire avec des politiques RLS qui interdisent l'accès aux données d'un autre compte.

Dans Supabase, relever l'URL du projet et la clé publishable/anon. Les ajouter aux secrets de l'hébergeur sous les noms :
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SOWIA_PUBLIC_URL` (URL HTTPS de l'application après déploiement)

La clé `service_role` ne doit jamais être envoyée au navigateur, affichée dans l'interface ou commitée dans Git. Pour l'écriture serveur des droits Premium, elle peut être stockée exclusivement dans les secrets privés de Streamlit sous `SUPABASE_SERVICE_ROLE_KEY`.

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
SOWIA_REQUIRE_AUTH = "true"
OPENAI_API_KEY = "<clé-API-privée>"
```

Le Client ID et le Client Secret GitHub sont enregistrés uniquement dans les paramètres du fournisseur GitHub de Supabase, jamais dans les secrets de l'application si Supabase gère le callback OAuth.

## 5. État de préparation

Le bouton de connexion GitHub, le callback PKCE et les appels de mémoire/historique cloud sont raccordés à l'interface. Ils restent à valider sur une URL HTTPS réelle avec un projet Supabase configuré. L'historique et la mémoire SQLite existants ne sont jamais importés automatiquement : ils restent inchangés jusqu'à une migration contrôlée. Les clés OpenAI/Tavily, si utilisées, doivent être ajoutées uniquement aux secrets de l'hébergeur.

Aucune clé, aucun mot de passe et aucun secret n'est requis dans ce dépôt.


## 6. Préparer PayPal Premium (mode test uniquement au départ)

Le module `paypal_payments.py` prépare les appels serveur à l'API PayPal Orders v2. Le secret PayPal et le jeton OAuth restent côté serveur ; le navigateur ne reçoit que le lien d'approbation. Le serveur revérifie le compte SOW IA, le produit, le montant et la devise avant de capturer une commande. Voir la documentation officielle : https://developer.paypal.com/api/rest/integration/orders-api

Dans PayPal Developer, créer une application REST en mode **Sandbox** et récupérer son Client ID et son Secret. Ajouter les paramètres suivants aux secrets Streamlit (ne jamais les publier dans GitHub ni les envoyer dans une conversation) :

```toml
PAYPAL_CLIENT_ID = "<client-id-sandbox>"
PAYPAL_CLIENT_SECRET = "<secret-sandbox>"
PAYPAL_MODE = "sandbox"
PAYPAL_PREMIUM_PRICE = "<prix-à-définir-en-euros>"
PAYPAL_CURRENCY = "EUR"
PAYPAL_RETURN_URL = "https://<adresse-deploiement>/?paypal=return"
PAYPAL_CANCEL_URL = "https://<adresse-deploiement>/?paypal=cancel"
```

**État actuel : les paiements sont volontairement désactivés.** Le réglage serveur `SOWIA_PAYMENTS_ENABLED` vaut `false` par défaut ; en son absence, aucune commande PayPal ne peut être créée ni capturée, même si des identifiants PayPal existent. Ne pas ajouter de secrets PayPal ni activer ce réglage pendant la phase actuelle du projet. L’interface indique que les paiements sont désactivés.

Lorsque l’application sera terminée et que l’administrateur décidera explicitement d’ouvrir les paiements, il faudra alors seulement préparer les identifiants PayPal, vérifier la table `sowia_entitlements` créée par `supabase/schema.sql`, stocker `SUPABASE_SERVICE_ROLE_KEY` exclusivement dans les secrets privés de Streamlit et activer `SOWIA_PAYMENTS_ENABLED=true`. Le service-role reste côté serveur. Le serveur vérifie le compte, le produit, le montant et la devise avant capture ; une redirection seule ne donne jamais accès. Commencer par Sandbox et ne passer en Live qu’après validation des achats et remboursements. Cette activation future est une étape distincte et n’est pas effectuée par cette modification.

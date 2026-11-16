# SOW IA — audit de réutilisation des fonctions pour Android

**Statut :** audit statique du dépôt `main`, réalisé à partir du code source. Il ne remplace pas les tests sur l'instance Supabase réelle ni les essais sur appareil. Aucune API mobile n'est déclarée comme déjà disponible.

## 1. Résultat exécutif

Le dépôt possède déjà plusieurs briques métier réutilisables : authentification Supabase, historique/mémoire, registre de projets, stockage privé de PDF, extraction PDF, assistant IA et recherche web. En revanche, une grande partie de leur orchestration est encore liée à Streamlit ou à des clients Python Supabase. Une application Android Kotlin ne peut pas appeler directement ces modules Python.

**Conclusion :** réutiliser les règles métier et le modèle de données, mais exposer progressivement les fonctions nécessaires via une couche serveur HTTPS documentée. Garder l'application Streamlit existante comme client web pendant cette évolution.

## 2. Matrice de réutilisation

| Fonction existante | Code repéré | Réutilisation Android | Travail préalable |
|---|---|---|---|
| Connexion / identité | `sowia_supabase_auth.py` | Réutiliser Supabase Auth et les mêmes comptes | Créer un flux OAuth natif PKCE Android ; ne pas reprendre le composant navigateur Streamlit ni sa persistance SQLite |
| Conversations / historique | `cloud_storage.py`, `storage.py` | Réutiliser le modèle et les données Supabase | API versionnée pour lister, lire, créer et supprimer les messages ; pagination et contrôle de session |
| Mémoire | `cloud_storage.py` | Réutiliser les enregistrements et limites métier | API authentifiée ; limiter les données retournées et respecter l'espace personnel/professionnel |
| Projets | `project_registry.py`, migration `20261114000100_sowia_project_register.sql` | Réutilisable en priorité | API CRUD avec propriété utilisateur, espace de travail, statuts, archivage et règles RLS |
| PDF privés | `document_storage.py`, `supabase/storage.sql` | Réutiliser le bucket privé et les chemins par utilisateur/espace | API de téléversement/liste/téléchargement/suppression ; liens signés courts si utilisés ; tester les politiques Storage |
| Extraction / OCR | `documents.py` | Réutiliser le traitement Python côté serveur | Exécuter hors interface Streamlit, limites de taille/pages/temps, file d'attente si charge importante |
| Assistant IA | `assistant.py`, `config.py` | Réutiliser le moteur et les fournisseurs côté serveur | API de génération ; clés IA exclusivement côté serveur ; limites de débit, délais, coût et erreurs 429 |
| Recherche web | `websearch.py` | Réutiliser côté serveur | API contrôlée ; clé Tavily uniquement serveur ; quotas et validation de requête |
| Droits Premium / professionnel | `premium_access.py`, migrations Supabase | Réutiliser le contrôle de droits serveur | Contrôle d'accès à chaque requête ; aucun droit déclaré depuis le client ; paiements exclus du prototype initial |
| Déconnexion / session | `session_security.py`, `sowia_supabase_auth.py` | Reproduire le résultat fonctionnel, pas le mécanisme Streamlit | Révoquer/terminer la session côté fournisseur et effacer jetons, cache et données privées locales |
| Navigation / interface | `app.py`, `project_registry_ui.py` | Réutiliser les parcours et le vocabulaire | Réécrire la présentation en Compose ; bouton Retour natif, état de navigation et conservation des brouillons |

## 3. Constats techniques importants

### Authentification
Le module actuel utilise un composant Streamlit v2 et un identifiant de navigateur stocké dans `localStorage` pour retrouver un vérificateur PKCE temporaire côté serveur. Ce flux est spécifique au navigateur web. Android doit utiliser le navigateur système et une redirection native/app-link avec PKCE, sans partager le stockage du navigateur Streamlit.

### Historique et mémoire
Le dépôt dispose de fonctions Supabase côté Python, avec filtrage par identifiant utilisateur et espace de travail. Le client Android ne doit pas recevoir de clé de service. Le serveur doit valider le jeton utilisateur et laisser RLS appliquer l'isolation des lignes.

### Projets
Le registre contient déjà les états « En cours », « À tester », « Validé » et « Terminé », les espaces personnel/professionnel, les livrables et l'archivage. C'est un bon premier parcours vertical Android après le socle de connexion.

### Documents PDF
Le bucket `sowia-files` est privé et le code limite les PDF à 10 Mo et 500 pages. L'extraction OCR est limitée à 30 pages. Ces règles sont à conserver et à compléter par des limites de durée, de mémoire et de concurrence côté serveur. Ne pas exposer de lien public permanent.

### Assistant et recherche web
Les modules utilisent des clés et des appels fournisseurs qui doivent rester côté serveur. Le client mobile ne doit jamais contenir de clé OpenAI, Groq, Tavily, PayPal ou Supabase `service_role`. Le quota IA épuisé doit être présenté clairement ; l'application ne doit pas prétendre qu'une réponse générative a été produite.

### Espaces et droits
Le code distingue `personal` et `professional`. Le contrôle Premium doit être vérifié côté serveur pour chaque opération professionnelle, pas uniquement en masquant un écran Android.

## 4. Ordre conseillé des premiers parcours Android

1. **Connexion / déconnexion / profil** — valider le cycle de session et la suppression des données locales.
2. **Mes échanges & projets** — commencer par la lecture du registre de projets et de l'historique, avec pagination et isolation multi-comptes.
3. **Assistant** — envoyer un message via API serveur, récupérer la réponse et gérer erreurs/quotas.
4. **PDF** — importer un document privé, suivre son traitement, afficher le résultat, télécharger ou supprimer.
5. **Mémoire et recherche web** — ajouter après validation des parcours précédents.
6. **Premium / paiements** — hors prototype initial, après validation juridique et règles Google Play.

## 5. Contrats API minimaux à spécifier

Les chemins ci-dessous sont des propositions, pas des endpoints déjà implémentés.

| Endpoint proposé | Usage | Sécurité attendue |
|---|---|---|
| `GET /api/v1/me` | Profil et capacités | Jeton utilisateur vérifié |
| `GET /api/v1/projects` | Liste paginée des projets | Propriété utilisateur + droits d'espace |
| `POST /api/v1/projects` | Créer un projet | Validation des champs + RLS |
| `PATCH /api/v1/projects/{id}` | Modifier statut/détails | Propriété et espace revérifiés |
| `GET /api/v1/conversations` | Lister les échanges | Propriété utilisateur |
| `POST /api/v1/conversations/{id}/messages` | Envoyer un message | Quota, taille, droits et clé IA serveur |
| `POST /api/v1/documents` | Importer un PDF | Auth, 10 Mo max, validation PDF |
| `GET /api/v1/documents` | Lister les PDF | Métadonnées de l'utilisateur uniquement |
| `GET /api/v1/documents/{id}` | Télécharger un PDF | Autorisation par objet, URL signée courte si besoin |
| `DELETE /api/v1/documents/{id}` | Supprimer un PDF | Autorisation par objet et confirmation |

Chaque contrat doit définir les schémas JSON, codes d'erreur, limites, pagination, délais, journaux et tests. Les identifiants fournis par le client ne constituent jamais une preuve de propriété.

## 6. Vérifications encore nécessaires avant développement

- Exécuter l'ensemble des tests du dépôt dans un environnement propre.
- Exécuter les tests d'intégration Supabase avec deux comptes réels ; les tests qui nécessitent des secrets de projet ne sont pas validés par une simple inspection statique.
- Vérifier les politiques RLS et Storage effectivement déployées sur le projet Supabase, pas seulement les fichiers SQL du dépôt.
- Vérifier que les migrations nécessaires sont appliquées sur le projet réel.
- Tester la déconnexion réelle et le retour OAuth sur l'instance web actuellement publiée.
- Mesurer les temps de réponse et limites des parcours PDF et IA.
- Définir l'hébergement des API et la supervision avant d'ouvrir des endpoints mobiles.

## 7. Ce qui n'a pas été fait

- Aucun endpoint API mobile n'a été créé par cet audit.
- Aucun code Kotlin/Compose, APK ou AAB n'a été créé.
- Aucune migration de données ni modification du schéma Supabase n'a été effectuée.
- Aucun changement n'a été déployé sur l'application web.
- Aucun test sur appareil Android ni test sur le projet Supabase réel n'est revendiqué.

## 8. Porte de validation

La première tranche de développement doit se limiter au parcours de connexion natif et à une API de profil/projets en lecture. Elle ne commence qu'après vérification des politiques réelles et choix de l'hébergement serveur. Cette séquence réduit les risques et préserve l'application web en production.

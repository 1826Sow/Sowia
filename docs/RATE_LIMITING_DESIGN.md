# SOW IA — conception du limiteur de requêtes partagé

## État et périmètre

Document de conception uniquement. Aucune table, fonction SQL, politique RLS, clé, variable Streamlit ou donnée de production n'est modifiée par ce document. Le limiteur n'est pas encore actif et aucun quota n'est annoncé comme appliqué.

Le besoin est de compter les opérations par **utilisateur authentifié et catégorie d'opération**, de façon atomique et partagée entre onglets, appareils et workers. Un compteur dans `st.session_state`, un dictionnaire Python, un cache local ou un fichier local ne répond pas à ce besoin.

## Points d'entrée recensés dans `app.py`

| Opération | Point d'appel | Catégorie proposée |
|---|---:|---|
| Assistant IA | 311 | `assistant` |
| Question/analyse PDF via IA | 467 | `pdf_question` |
| Analyse PDF avancée Premium | 442 | `advanced_pdf` |
| Analyse groupée PDF Premium | 514 | `batch_pdf` |
| Recherche Web | 409 | `web_search` |
| Téléversement document privé | 656 | `document_upload` |
| Téléchargement document privé | 687 | `document_download` |
| Suppression document privé | 691 | `document_delete` |

Les analyses Premium vérifient déjà le droit Premium côté serveur avant l'appel IA. Le limiteur devra être appelé après l'identification authentifiée, et avant tout appel fournisseur, écriture, lecture coûteuse ou suppression. La préparation locale des PDF doit conserver ses limites de taille même si le quota réseau est refusé.

## Architecture retenue à valider sur un projet Supabase isolé

1. Une table privée `public.sowia_rate_limits`, clé primaire composée de `user_id` et `bucket_key`, contenant le début de fenêtre et le compteur.
2. Une fonction RPC `public.sowia_consume_rate_limit(p_bucket_key text, p_window_seconds integer, p_limit integer)` qui exécute une seule opération atomique `INSERT ... ON CONFLICT ... DO UPDATE ... RETURNING`.
3. La fonction vérifie `auth.uid()` et refuse toute identité absente. Le client authentifié ne reçoit aucun droit direct de lecture/écriture sur la table.
4. La fonction est créée avec un `search_path` fixe et minimal, et son exécution est accordée uniquement au rôle `authenticated`. Aucun secret service-role n'est transmis au navigateur.
5. Le compteur est partagé par tous les onglets/appareils du même compte. Les clés de compartiment sont choisies par le code serveur dans une liste fermée, jamais fournies librement par le navigateur.
6. En production, après validation isolée et déploiement coordonné du SQL et du code, une erreur RPC doit refuser l'opération protégée (fail closed) avec un message utilisateur neutre. Ne jamais basculer silencieusement vers un compteur local.

### Esquisse SQL — non exécutable / non déployée

La logique à prototyper dans le projet isolé est :

```sql
-- Table privée : pas de privilèges directs pour anon/authenticated.
create table public.sowia_rate_limits (
    user_id uuid not null references auth.users(id) on delete cascade,
    bucket_key text not null,
    window_started_at timestamptz not null,
    request_count integer not null check (request_count >= 0),
    primary key (user_id, bucket_key)
);

-- RPC SECURITY DEFINER avec search_path fixe :
-- 1. vérifier auth.uid() IS NOT NULL ;
-- 2. valider bucket_key dans une allowlist et des bornes strictes ;
-- 3. atomiquement insérer ou incrémenter la fenêtre ;
-- 4. si la fenêtre est expirée, la réinitialiser à now() et count=1 ;
-- 5. retourner allowed, remaining, reset_at.
-- L'incrément doit être atomique dans le même statement/transaction.
-- REVOKE EXECUTE FROM PUBLIC, anon ; GRANT EXECUTE TO authenticated.
```

Ce fragment est une esquisse, pas une migration prête à exécuter. Le SQL final doit être écrit et testé sur un projet isolé avec deux comptes et plusieurs sessions concurrentes.

## Politique de limites à calibrer

Les seuils ci-dessous sont des valeurs de départ pour les tests, pas des limites actuellement actives :

| Compartiment | Fenêtre | Seuil de départ |
|---|---:|---:|
| Assistant IA | 60 secondes | 10 |
| Question PDF IA | 60 secondes | 5 |
| Analyse PDF avancée | 5 minutes | 3 |
| Analyse groupée PDF | 10 minutes | 2 |
| Recherche Web | 60 secondes | 5 |
| Téléversement document | 10 minutes | 5 |
| Téléchargement document | 60 secondes | 10 |
| Suppression document | 60 secondes | 5 |

Prévoir aussi un plafond quotidien pour les opérations facturables, à calibrer selon le fournisseur et les coûts réels. Ne pas prétendre qu'un quota de coût est garanti par le seul plafond par minute.

## Tests obligatoires avant activation

- Deux sessions du même utilisateur consomment le même compteur.
- Deux utilisateurs ont des compteurs strictement indépendants.
- Des appels concurrents ne peuvent pas dépasser le quota par course critique.
- Le compteur revient à zéro après expiration de la fenêtre.
- Une clé de compartiment inconnue, une fenêtre hors bornes ou une limite invalide est rejetée.
- Un utilisateur anonyme ne peut pas appeler la fonction.
- Un utilisateur ne peut pas lire, modifier ou supprimer directement les compteurs.
- Une panne RPC bloque l'opération protégée après activation, sans exposer les détails techniques.
- Les contrôles Premium existants restent obligatoires ; le rate limiting ne remplace jamais l'autorisation.

## Déploiement sûr

1. Créer un projet Supabase séparé de production.
2. Inspecter rôles, privilèges, RLS et fonctions avant migration.
3. Appliquer la migration uniquement dans ce projet isolé.
4. Tester les cas ci-dessus, y compris les appels simultanés multi-session.
5. Vérifier les performances et le nettoyage périodique des fenêtres expirées.
6. Soumettre le SQL et le code ensemble dans la PR, faire relire, puis attendre une validation explicite avant toute fusion.
7. Ne jamais activer le limiteur côté application tant que la RPC n'existe pas et n'a pas été validée dans l'environnement cible.

## Hors périmètre

- Aucun changement du schéma Supabase de production.
- Aucun changement OAuth, secret Streamlit ou clé API.
- Aucun appel réel PayPal ; les paiements restent désactivés.
- Aucune activation ou fusion automatique de la PR.

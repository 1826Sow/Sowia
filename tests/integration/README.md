# Tests d'intégration Supabase (schéma actuel)

Les tests d'intégration vérifient les politiques RLS réellement appliquées aux tables `public.sowia_messages` et `public.sowia_memory_items`, ainsi que l'isolation du bucket privé `sowia-files` pour les PDF.

## Préparation sûre

1. Utiliser un projet Supabase de test dédié, jamais la base de production.
2. Dans **Authentication → Users**, créer deux comptes de test distincts (A et B) avec des adresses et mots de passe dédiés. Vérifier que les deux comptes peuvent se connecter.
3. Dans le **SQL Editor** de ce projet de test, exécuter dans cet ordre :
   - `supabase/schema.sql` (tables, RLS et droits de lecture Premium).
   - `supabase_workspaces.sql` (ajout des espaces Personnel et Professionnel).
   - `supabase_storage_policies.sql` (création du bucket privé `sowia-files` et règles d'accès PDF).
4. Dans les paramètres API du projet de test, récupérer l'URL du projet et la clé publique **anon/publishable**. Ne pas utiliser la clé `service_role` ou une clé secrète.
5. Fournir les sept variables ci-dessous uniquement dans l'environnement d'exécution sécurisé :

```text
SOWIA_TEST_SUPABASE_URL
SOWIA_TEST_SUPABASE_ANON_KEY
SOWIA_TEST_USER_A_EMAIL
SOWIA_TEST_USER_A_PASSWORD
SOWIA_TEST_USER_B_EMAIL
SOWIA_TEST_USER_B_PASSWORD
SOWIA_TEST_PROJECT_CONFIRMATION
```

Pour `SOWIA_TEST_PROJECT_CONFIRMATION`, utiliser exactement la valeur `I_CONFIRM_THIS_IS_A_DEDICATED_SOWIA_TEST_PROJECT` uniquement après avoir vérifié l'URL et le projet Supabase de test. Cette confirmation supplémentaire est obligatoire : sans elle, aucun appel réseau de test n'est effectué. Les scripts n'acceptent qu'une URL de projet hébergé au format HTTPS `https://<projet>.supabase.co`, sans identifiants, port, chemin, paramètres ni fragment. Les redirections HTTP sont désactivées pour empêcher le transfert involontaire des clés ou jetons vers une autre destination.

Ne jamais utiliser les comptes de production, ni inscrire les secrets dans Git, les journaux CI ou une capture d'écran. Le projet de test doit rester distinct de l'application SOW IA en production.

## Exécution locale

Depuis la racine du dépôt :

```bash
pytest -q tests/integration/test_supabase_two_user_isolation.py tests/integration/test_supabase_storage_two_user_isolation.py
```

## Exécution automatique dans GitHub Actions

Dans GitHub, ouvrir **Settings → Secrets and variables → Actions**, puis créer les sept secrets portant exactement les noms listés plus haut. Leurs valeurs doivent provenir exclusivement du projet Supabase de test et de ses deux comptes dédiés.

**Protection des secrets :** le job des tests RLS réels est conditionné aux seuls événements `push` sur la branche `main`. Il ne reçoit donc aucun secret pendant les événements `pull_request`, où le code proposé peut être non fiable. Les tests automatisés ordinaires continuent de s'exécuter sur les PR sans secrets. En conséquence, une PR ne valide pas l'isolation Supabase réelle ; celle-ci ne sera testée qu'après un push fiable sur `main`, si les sept secrets sont configurés.

Si l'un des six identifiants ou la confirmation dédiée manque ou est incorrect, le job indique explicitement que les tests réels sont ignorés ; il ne prétend jamais avoir validé la RLS. Ne jamais renseigner les identifiants d'un compte réel ni ceux du projet de production.

Avec les sept variables, deux sessions authentifiées vérifient pour chaque table que le compte A peut lire ses propres lignes, que le compte B ne peut pas les lire, qu'il ne peut pas insérer une ligne au nom de A et qu'il ne peut pas supprimer la ligne de A. Les lignes témoins créées sont supprimées par le compte A dans un bloc `finally`.

Le test Storage utilise les mêmes sept secrets, vérifie que le compte A peut déposer et télécharger son PDF, que B ne peut ni le télécharger, ni déposer un fichier dans le dossier de A, ni supprimer le PDF de A. Le propriétaire supprime le fichier temporaire dans un bloc `finally`. Il cible le bucket `sowia-files` et les chemins `<user_id>/personal/<fichier>`.

Un test ignoré ne constitue pas une validation RLS réelle. La validation exige un projet de test configuré et un résultat d'exécution réussi.

## Diagnostic préalable des politiques et privilèges (lecture seule)

Avant de configurer les sept secrets CI, exécuter `supabase_security_diagnostics.sql` dans le SQL Editor du projet de test, avec un rôle administrateur. Le script est strictement en lecture seule : il inventorie toutes les politiques de `storage.objects` et des tables privées `sowia_messages`, `sowia_memory_items` et `sowia_entitlements`, l'état RLS, les privilèges sur les tables et séquences, ainsi que la configuration du bucket `sowia-files`.

Examiner chaque politique Storage, quel que soit son nom : les politiques permissives sont combinées par OR. Toute politique trop large doit être comprise et corrigée dans le projet de test avant d'exécuter les tests à deux comptes. Vérifier également que `sowia_entitlements` n'accorde pas d'écriture à `authenticated`, que `anon` n'a aucun accès aux données privées et que le bucket reste privé.

Le script ne modifie rien et ne certifie pas automatiquement la sécurité. Conserver les résultats de diagnostic sans y inclure de secrets ni de données personnelles ; faire vérifier les expressions de politiques et les privilèges avant de poursuivre.

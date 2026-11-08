# Tests d'intégration Supabase (schéma actuel)

Les tests d'intégration vérifient les politiques RLS réellement appliquées aux tables `public.sowia_messages` et `public.sowia_memory_items`, ainsi que l'isolation du bucket privé `sowia-files` pour les PDF.

## Préparation sûre

1. Utiliser un projet Supabase de test dédié, jamais la base de production.
2. Créer deux comptes de test distincts dans Supabase Authentication.
3. Exécuter sur ce projet les scripts `supabase/schema.sql` puis `supabase_workspaces.sql`.
4. Fournir les six variables ci-dessous uniquement dans l'environnement d'exécution sécurisé :

```text
SOWIA_TEST_SUPABASE_URL
SOWIA_TEST_SUPABASE_ANON_KEY
SOWIA_TEST_USER_A_EMAIL
SOWIA_TEST_USER_A_PASSWORD
SOWIA_TEST_USER_B_EMAIL
SOWIA_TEST_USER_B_PASSWORD
```

Utiliser uniquement la clé publique anon/publishable. Ne jamais utiliser une clé `service_role`, ni inscrire les secrets dans Git, les journaux CI ou une capture d'écran.

## Exécution locale

Depuis la racine du dépôt :

```bash
pytest -q tests/integration/test_supabase_two_user_isolation.py tests/integration/test_supabase_storage_two_user_isolation.py
```

## Exécution automatique dans GitHub Actions

Dans GitHub, ouvrir **Settings → Secrets and variables → Actions**, puis créer les six secrets portant exactement les noms listés plus haut. Leurs valeurs doivent provenir exclusivement du projet Supabase de test et de ses deux comptes dédiés.

L'action GitHub lance alors les tests réels entre les deux comptes à chaque push/PR. Si les six secrets ne sont pas configurés, le job indique explicitement que les tests réels sont ignorés ; il ne prétend jamais avoir validé la RLS. Ne jamais renseigner les identifiants d'un compte réel ni ceux du projet de production.

Avec les six variables, deux sessions authentifiées vérifient pour chaque table que le compte A peut lire ses propres lignes, que le compte B ne peut pas les lire, qu'il ne peut pas insérer une ligne au nom de A et qu'il ne peut pas supprimer la ligne de A. Les lignes témoins créées sont supprimées par le compte A dans un bloc `finally`.

Le test Storage utilise les mêmes six secrets, vérifie que le compte A peut déposer et télécharger son PDF, que B ne peut ni le télécharger, ni déposer un fichier dans le dossier de A, ni supprimer le PDF de A. Le propriétaire supprime le fichier temporaire dans un bloc `finally`. Il cible le bucket `sowia-files` et les chemins `<user_id>/personal/<fichier>`.

Un test ignoré ne constitue pas une validation RLS réelle. La validation exige un projet de test configuré et un résultat d'exécution réussi.

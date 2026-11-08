# Tests d'intégration Supabase (schéma actuel)

Le test `test_supabase_two_user_isolation.py` vérifie les politiques RLS réellement appliquées aux deux tables utilisées par le code actuel : `public.sowia_messages` et `public.sowia_memory_items`.

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

## Exécution

Depuis la racine du dépôt :

```bash
pytest -q tests/integration/test_supabase_two_user_isolation.py
```

Sans les six variables, les tests sont ignorés. Avec elles, deux sessions authentifiées vérifient pour chaque table que le compte A peut lire ses propres lignes, que le compte B ne peut pas les lire, qu'il ne peut pas insérer une ligne au nom de A et qu'il ne peut pas supprimer la ligne de A. Les lignes témoins créées sont supprimées par le compte A dans un bloc `finally`.

Les tests ciblent uniquement les tables réellement créées par le schéma courant. Ils ne prétendent pas valider le stockage PDF Supabase Storage, qui dispose de son propre diagnostic en lecture seule.

Un test ignoré dans la CI standard ne constitue pas une validation RLS réelle. La validation exige un projet de test configuré et un résultat d'exécution réussi.

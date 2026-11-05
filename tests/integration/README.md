# Tests d'intégration Supabase

Le test `test_supabase_two_user_isolation.py` vérifie réellement les politiques RLS de `public.sowia_documents` avec deux sessions authentifiées distinctes.

## Préparation sûre

1. Utiliser un projet Supabase de test, jamais la base de production.
2. Créer deux comptes de test distincts dans Supabase Authentication.
3. Appliquer les migrations documentaires du dépôt sur ce projet de test.
4. Fournir les six variables d'environnement ci-dessous uniquement dans l'environnement d'exécution sécurisé :

```text
SOWIA_TEST_SUPABASE_URL
SOWIA_TEST_SUPABASE_ANON_KEY
SOWIA_TEST_USER_A_EMAIL
SOWIA_TEST_USER_A_PASSWORD
SOWIA_TEST_USER_B_EMAIL
SOWIA_TEST_USER_B_PASSWORD
```

Utiliser exclusivement la clé publique `anon`/publishable. Ne jamais utiliser ni communiquer une clé `service_role`. Ne pas inscrire les valeurs dans Git, dans les journaux CI ou dans une capture d'écran.

## Exécution

Depuis la racine du dépôt :

```bash
pytest -q tests/integration/test_supabase_two_user_isolation.py
```

Sans les six variables, le test est automatiquement ignoré. Avec elles, il crée un document témoin temporaire sous le compte A, vérifie que B ne peut ni le lire, ni créer un document au nom de A, ni le modifier ou le supprimer, puis supprime le document témoin avec le compte A.

Le test ne crée pas les comptes et ne modifie pas les migrations. Il utilise des comptes dédiés à l'intégration. Même si le nettoyage est prévu dans `finally`, lancer uniquement sur un projet de test isolé.

Un test ignoré dans la CI standard n'est pas une validation RLS en production : la validation réelle exige un environnement de test configuré et un résultat d'exécution réussi.

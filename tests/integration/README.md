# Tests d'intégration Supabase (schéma actuel)

Les tests d'intégration vérifient les politiques RLS réellement appliquées entre deux comptes authentifiés :
- `public.sowia_messages` et `public.sowia_memory_items` ;
- le bucket privé `sowia-files` pour les PDF ;
- `public.sowia_financial_transactions` et `public.sowia_subscriptions`.

## Préparation sûre

1. Utiliser un projet Supabase de test dédié, jamais la base de production.
2. Dans **Authentication → Users**, créer deux comptes de test distincts (A et B) avec des adresses et mots de passe dédiés. Vérifier que les deux comptes peuvent se connecter.
3. Dans le **SQL Editor** du projet de test, appliquer le schéma et les migrations nécessaires dans l'ordre du dépôt. Pour les deux nouvelles tables testées, les migrations minimales sont :
   - `supabase/migrations/20261109000100_sowia_subscriptions.sql`
   - `supabase/migrations/20261110000100_sowia_financial_ledger.sql`
   Pour les tests messages/mémoire/PDF, appliquer aussi :
   - `supabase/schema.sql`
   - `supabase_workspaces.sql`
   - `supabase_storage_policies.sql`
   Les autres migrations PayPal doivent être appliquées dans l'ordre lorsqu'on prépare un environnement complet de l'application.
4. Dans les paramètres API du projet de test, récupérer l'URL du projet, la clé publique **anon/publishable** et la clé **service_role** propre à ce projet de test.
5. Fournir les sept variables d'identification ci-dessous et la variable de confirmation dans l'environnement d'exécution sécurisé :

```text
SOWIA_TEST_SUPABASE_URL
SOWIA_TEST_SUPABASE_ANON_KEY
SOWIA_TEST_SUPABASE_SERVICE_ROLE_KEY
SOWIA_TEST_USER_A_EMAIL
SOWIA_TEST_USER_A_PASSWORD
SOWIA_TEST_USER_B_EMAIL
SOWIA_TEST_USER_B_PASSWORD
SOWIA_TEST_PROJECT_CONFIRMATION
```

Pour la dernière variable, utiliser exactement la valeur :
`I_CONFIRM_THIS_IS_A_DEDICATED_SOWIA_TEST_PROJECT`

**La clé service_role est utilisée uniquement pour créer puis supprimer les lignes témoins des tests financiers/abonnement.** Les requêtes dont le but est de vérifier les droits d'un utilisateur utilisent toujours la clé publique et le JWT du compte A ou B. La clé service_role doit provenir exclusivement du projet jetable de test ; ne jamais utiliser celle de production. Ne jamais inscrire les secrets dans Git, les journaux CI ou une capture d'écran.

## Exécution locale

Depuis la racine du dépôt, avec les huit variables définies :

```bash
pytest -q tests/integration/
```

## Exécution automatique dans GitHub Actions

Dans GitHub, ouvrir **Settings → Secrets and variables → Actions**, puis créer les huit secrets portant exactement les noms listés plus haut. Leurs valeurs doivent provenir exclusivement du projet Supabase de test et de ses deux comptes dédiés.

Les tests réels sont lancés sur les pushes de la branche de consolidation `security/hardening-clean` et de `main`. Ils ne sont volontairement pas lancés sur les événements `pull_request`, afin de ne jamais exposer les secrets Supabase au code d'une pull request. Si un secret manque ou si la confirmation explicite est incorrecte, le job signale que les tests sont ignorés ; il ne prétend jamais avoir validé la RLS. Ne jamais renseigner les identifiants d'un compte réel ni ceux du projet de production.

Le job exécute les trois suites :
- messages et mémoire : A lit ses propres lignes, B ne les lit pas, ne peut pas insérer une ligne au nom de A et ne peut pas supprimer la ligne de A ;
- PDF : A peut déposer et télécharger son fichier, B ne peut ni le télécharger, ni déposer dans le dossier de A, ni supprimer le PDF de A ;
- transactions financières et abonnements : des lignes témoins sont créées par le rôle administrateur du projet de test, puis les sessions authentifiées A/B vérifient la lecture limitée au propriétaire, le refus des écritures client et l'impossibilité pour B de supprimer la ligne de A.

Les lignes témoins financières et abonnement sont supprimées par le rôle administrateur de test dans un bloc `finally`. Les tests PDF et les tests messages/mémoire nettoient également leurs propres données temporaires.

Un test ignoré ne constitue pas une validation RLS réelle. La validation exige un projet de test configuré et un résultat d'exécution réussi pour les trois suites.

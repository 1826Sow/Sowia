# Déploiement contrôlé — liaison des paiements PayPal aux abonnements

## Objectif

Appliquer la migration `20261111000100_paypal_billing_ledger_link.sql` afin que les échéances PayPal enregistrées dans `public.sowia_financial_transactions` conservent l'identifiant de leur abonnement.

Cette migration est additive : elle ajoute une colonne nullable et un index partiel. Elle ne met à jour ni ne supprime aucune transaction existante.

## Règles de sécurité

- Ne pas exécuter cette procédure sur la production avant validation sur un projet Supabase de test.
- Ne jamais copier une clé `service_role`, un mot de passe ou un secret dans GitHub, un ticket ou une conversation.
- Ne pas activer de paiements, remboursements ou webhooks réels pendant cette vérification.
- Si la table ou la structure attendue n'existe pas, arrêter et examiner le schéma avant toute exécution.

## Étape 1 — vérifier le schéma dans le projet Supabase de test

Dans **SQL Editor**, exécuter d'abord :

```sql
select table_schema, table_name
from information_schema.tables
where table_schema = 'public'
  and table_name = 'sowia_financial_transactions';
```

Le résultat doit contenir exactement la table attendue. Sinon, arrêter.

## Étape 2 — appliquer la migration sur le projet de test

Après vérification de la table, exécuter le contenu du fichier :

`supabase/migrations/20261111000100_paypal_billing_ledger_link.sql`

Le script utilise `IF NOT EXISTS` pour rendre l'ajout de colonne et d'index répétable.

## Étape 3 — vérifier le résultat

```sql
select column_name, data_type, is_nullable
from information_schema.columns
where table_schema = 'public'
  and table_name = 'sowia_financial_transactions'
  and column_name = 'paypal_subscription_id';

select indexname, indexdef
from pg_indexes
where schemaname = 'public'
  and tablename = 'sowia_financial_transactions'
  and indexname = 'sowia_financial_transactions_paypal_subscription_idx';
```

Résultat attendu : une colonne `text` nullable et l'index partiel portant le nom indiqué.

## Étape 4 — tests applicatifs

Après la migration de test, lancer les tests automatisés du dépôt et, lorsque le projet de test et deux comptes dédiés sont configurés, les tests RLS à deux utilisateurs décrits dans `tests/integration/README.md`.

Un job RLS ignoré n'est pas une validation de l'isolation réelle.

## Retour arrière

Ne pas supprimer la colonne ni l'index comme première réaction : les versions récentes de l'application peuvent déjà lire ou écrire la colonne. En cas d'anomalie, suspendre les opérations de synchronisation concernées et examiner les journaux avant toute modification du schéma.

## État de suivi

- Migration versionnée dans Git : oui.
- Vérification automatisée du code : réussie sur le commit associé au changement.
- Migration exécutée sur Supabase de test : non confirmée.
- Migration exécutée en production : non effectuée.
- Paiements réels ou remboursements déclenchés : non.

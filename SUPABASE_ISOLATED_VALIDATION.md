# Validation isolée Supabase — SOW IA

> **Sécurité impérative :** ce protocole est réservé à un projet Supabase de test distinct du projet de production. Ne pas exécuter le SQL de cette PR sur le projet actuellement utilisé par SOW IA. Ne jamais copier ici une clé service-role, un secret OAuth ou un mot de passe.

## Objectif

Vérifier en conditions réelles les politiques RLS de stockage PDF privé et de lecture des droits Premium avant toute fusion ou migration de production.

## Préparation du projet de test

1. Créer ou choisir un projet Supabase temporaire, clairement nommé `SOW IA - TEST`.
2. Vérifier deux fois son nom et son identifiant dans le tableau de bord avant toute action SQL.
3. Créer deux comptes de test distincts : Utilisateur A et Utilisateur B.
4. Dans l'éditeur SQL de **ce projet de test uniquement**, exécuter d'abord les requêtes de précontrôle en lecture seule présentées plus bas dans la section « Précontrôle en lecture seule des politiques déjà présentes ».
5. Examiner les résultats : si une politique inconnue ou permissive est présente, ou si le bucket existe déjà avec une configuration ou un usage non vérifié, arrêter la procédure et analyser avant toute modification.
6. Seulement si le précontrôle est sûr, exécuter `supabase_optional_features.sql` depuis la branche de la PR dans ce projet de test.
7. Vérifier dans Storage que le bucket `sowia-private-documents` est privé, limité à 10 485 760 octets et au type MIME `application/pdf`.
8. Ne pas ajouter de clé service-role dans le navigateur, dans un dépôt Git ou dans un message.

## Scénarios Storage à valider

Utiliser deux sessions navigateur distinctes, une connectée comme A et l'autre comme B.

| Test | Action | Résultat attendu |
|---|---|---|
| S1 | A téléverse un PDF valide sous le préfixe de son UID | Autorisé |
| S2 | A liste et télécharge son propre PDF | Autorisé |
| S3 | A supprime son propre PDF | Autorisé |
| S4 | B tente de lister ou télécharger le fichier de A | Refusé ou aucun fichier visible |
| S5 | B tente de supprimer ou modifier le fichier de A | Refusé |
| S6 | A tente d'écrire sous le préfixe UID de B | Refusé |
| S7 | Un utilisateur non connecté tente d'accéder au bucket | Refusé |
| S8 | Téléversement d'un fichier non PDF ou supérieur à 10 Mo | Refusé par l'application et/ou la limite Storage |

Pour S1 à S8, conserver uniquement les résultats et messages d'erreur expurgés. Ne pas conserver les jetons de session.

## Scénarios RLS des droits Premium

1. Avec A et B, créer les lignes de test uniquement via le client serveur de test ou une fixture contrôlée.
2. Vérifier qu'A peut lire sa propre ligne dans `sowia_entitlements`.
3. Vérifier que B ne peut ni lire la ligne d'A ni modifier ses droits.
4. Vérifier qu'un client authentifié standard ne peut pas insérer, modifier ou supprimer une ligne d'abonnement.
5. Vérifier qu'un utilisateur non authentifié ne peut pas lire la table.
6. Vérifier que l'accès applicatif est refusé si la ligne est absente, `inactive` ou `cancelled`, et autorisé uniquement si le statut est `active`. Le schéma SQL n'accepte volontairement que ces trois statuts ; une commande en attente ne doit pas créer de droit Premium.

## Critères de réussite

- Tous les scénarios S1 à S8 donnent le résultat attendu.
- Les droits Premium sont lisibles uniquement par leur propriétaire et modifiables uniquement par le serveur de confiance.
- Aucun secret ni fichier privé d'un autre compte n'est accessible.
- Les résultats sont consignés sans données personnelles ni jetons.

## En cas d'échec

Arrêter les essais, noter le scénario et le résultat observé, puis corriger la branche de la PR et relancer la CI. Ne pas contourner une politique RLS et ne pas tester en production.

## État au moment de la rédaction

- La CI automatisée du commit testé a réussi.
- Les tests présents dans le dépôt vérifient statiquement le SQL et ne constituent pas une validation RLS/Storage réelle.
- Aucun projet Supabase isolé n'a encore été validé.
- Aucune migration n'a été exécutée sur Supabase de production.
- La PR doit rester en brouillon et non fusionnée jusqu'à validation de cette procédure.

## Précontrôle en lecture seule des politiques déjà présentes

Avant d'exécuter le script de configuration, relever les politiques déjà présentes dans le projet de test. Les politiques permissives PostgreSQL peuvent s'additionner : une ancienne politique trop large sur `storage.objects` pourrait donc autoriser un accès que les nouvelles politiques ne bloquent pas.

Exécuter ces requêtes **en lecture seule**, dans le projet `SOW IA - TEST` uniquement :

```sql
-- Politiques existantes sur le stockage Supabase.
select schemaname, tablename, policyname, permissive, roles,
       cmd, qual, with_check
from pg_policies
where schemaname = 'storage'
  and tablename = 'objects'
order by policyname;

-- Politiques existantes sur la table des droits Premium.
select schemaname, tablename, policyname, permissive, roles,
       cmd, qual, with_check
from pg_policies
where schemaname = 'public'
  and tablename = 'sowia_entitlements'
order by policyname;

-- Configuration actuelle du bucket, s'il existe déjà.
select id, name, public, file_size_limit, allowed_mime_types
from storage.buckets
where id = 'sowia-private-documents';
```

### Décision avant migration

- Examiner chaque politique retournée, notamment celles accordant `SELECT`, `INSERT`, `UPDATE` ou `DELETE` à `anon`, `authenticated` ou `public`.
- Ne supprimer aucune politique inconnue ou préexistante automatiquement.
- Si une politique générale autorise un accès large, arrêter la procédure et analyser son origine et ses dépendances avant toute modification.
- Si le bucket n'existe pas, le script peut le créer avec les paramètres attendus.
- Si le bucket existe déjà, le script ne modifie désormais aucun de ses paramètres. Vérifier qu'il est privé, limité à 10 485 760 octets et au MIME `application/pdf`. En cas d'écart, arrêter la migration et examiner l'usage du bucket avant toute correction manuelle dans le projet de test.
- Conserver les résultats expurgés, sans identifiants personnels ni secrets.


## Contrôle complémentaire des tables de mémoire et d'historique

L'application utilise également les tables existantes `public.sowia_memory_items` et `public.sowia_messages`. Le script SQL de cette PR ne les crée pas et ne modifie pas leurs politiques : elles doivent donc être contrôlées séparément dans le projet isolé avant de considérer l'isolation des comptes comme validée.

Ajouter au précontrôle, toujours en lecture seule :

```sql
-- Vérifier l'existence et l'activation de RLS sur les deux tables.
select n.nspname as schema_name, c.relname as table_name,
       c.relrowsecurity as rls_enabled,
       c.relforcerowsecurity as rls_forced
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public'
  and c.relname in ('sowia_memory_items', 'sowia_messages')
order by c.relname;

-- Examiner toutes les politiques attachées à ces tables.
select schemaname, tablename, policyname, permissive, roles,
       cmd, qual, with_check
from pg_policies
where schemaname = 'public'
  and tablename in ('sowia_memory_items', 'sowia_messages')
order by tablename, policyname;

-- Vérifier les privilèges SQL accordés aux rôles applicatifs.
select table_schema, table_name, grantee, privilege_type
from information_schema.role_table_grants
where table_schema = 'public'
  and table_name in ('sowia_memory_items', 'sowia_messages')
  and grantee in ('anon', 'authenticated', 'public')
order by table_name, grantee, privilege_type;
```

Résultats attendus : les deux tables existent, RLS est activé, et les politiques/privilèges ne permettent à aucun compte de lire, modifier ou supprimer les données d'un autre utilisateur. Si RLS est désactivé, si une politique permissive est trop large, ou si les privilèges sont inattendus, arrêter les essais et analyser avant toute modification.

Ajouter ensuite ces essais avec les comptes A et B :

| Test | Action | Résultat attendu |
|---|---|---|
| M1 | A crée une note mémoire et relit ses notes | Autorisé |
| M2 | B tente de lire ou supprimer la note de A | Refusé ou aucune donnée de A visible |
| M3 | A enregistre et relit son historique de conversation | Autorisé |
| M4 | B tente de lire ou supprimer l'historique de A | Refusé ou aucune donnée de A visible |
| M5 | Un utilisateur non connecté tente d'accéder aux deux tables | Refusé |

Ne pas ajouter de politique ni modifier les tables sur la seule base de ces résultats sans avoir identifié leur schéma et leurs usages. Ce contrôle complète les scénarios Storage et Premium ; il ne les remplace pas.

Ce précontrôle ne remplace pas les scénarios S1 à S8 ni les essais RLS Premium. Il réduit le risque qu'une politique héritée ou un bucket déjà utilisé fausse la validation.

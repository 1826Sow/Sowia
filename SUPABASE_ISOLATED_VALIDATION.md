# Validation isolée Supabase — SOW IA

> **Sécurité impérative :** ce protocole est réservé à un projet Supabase de test distinct du projet de production. Ne pas exécuter le SQL de cette PR sur le projet actuellement utilisé par SOW IA. Ne jamais copier ici une clé service-role, un secret OAuth ou un mot de passe.

## Objectif

Vérifier en conditions réelles les politiques RLS de stockage PDF privé et de lecture des droits Premium avant toute fusion ou migration de production.

## Préparation du projet de test

1. Créer ou choisir un projet Supabase temporaire, clairement nommé `SOW IA - TEST`.
2. Vérifier deux fois son nom et son identifiant dans le tableau de bord avant toute action SQL.
3. Créer deux comptes de test distincts : Utilisateur A et Utilisateur B.
4. Dans l'éditeur SQL de **ce projet de test uniquement**, exécuter d'abord les requêtes de précontrôle en lecture seule présentées plus bas dans la section « Précontrôle en lecture seule des politiques déjà présentes ». Pour un projet neuf, l'absence des tables mémoire/historique et de leurs politiques est normale à ce stade ; ne pas exécuter la requête de contrôle de contrainte mémoire avant la création du schéma.
5. Examiner les résultats : si une politique inconnue ou permissive est présente, ou si le bucket existe déjà avec une configuration ou un usage non vérifié, arrêter la procédure et analyser avant toute modification.
6. Si les précontrôles sont sûrs, exécuter **d'abord** `supabase/schema.sql` depuis la branche de la PR dans ce projet isolé. C'est le schéma de base prévu pour les tables mémoire, historique et droits Premium.
7. Exécuter ensuite `supabase_optional_features.sql` depuis la branche de la PR dans ce même projet isolé pour configurer le bucket privé et réappliquer la politique de lecture Premium.
8. Ne pas exécuter le fichier racine historique `supabase_schema.sql` : il s'agit d'un ancien script, différent du schéma de base actuel et doté d'un octroi de privilèges de séquence plus large. Ne pas mélanger les deux scripts.
9. Après création du schéma, exécuter le contrôle de contrainte mémoire plus bas, puis vérifier dans Storage que le bucket `sowia-private-documents` est privé, limité à 10 485 760 octets et au type MIME `application/pdf`.
10. Ne pas ajouter de clé service-role dans le navigateur, dans un dépôt Git ou dans un message.

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

Le fichier `supabase/schema.sql` crée les tables `public.sowia_memory_items` et `public.sowia_messages` si elles sont absentes, active RLS et ajoute des politiques propriétaire, dont des garde-fous restrictifs contre les anciennes politiques permissives. Si ces tables existent déjà, `CREATE TABLE IF NOT EXISTS` ne répare pas leur schéma ni leurs anciennes politiques : le précontrôle ci-dessous reste donc obligatoire dans le projet isolé, avant et après l'application du script.

Effectuer ce contrôle en lecture seule avant le script pour inventorier l'état hérité, puis le répéter après le script pour confirmer l'activation RLS et les politiques finales :

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
  and upper(grantee) in ('ANON', 'AUTHENTICATED', 'PUBLIC')
order by table_name, grantee, privilege_type;
```

Avant le script, les tables peuvent être absentes dans un projet neuf. Après le script, les deux tables doivent exister, RLS doit être activé et les politiques doivent inclure les garde-fous restrictifs `SOW IA enforce own messages` et `SOW IA enforce own memory`. Vérifier également les privilèges SQL. Si une table existante présente une politique ou un privilège inattendu, arrêter et analyser avant toute modification ; ne pas considérer le simple succès du script comme une preuve d'isolation. Si RLS est désactivé, si une politique permissive est trop large, ou si les privilèges sont inattendus, arrêter les essais et analyser avant toute modification.

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


## Compatibilité des séquences SQL héritées

Le schéma courant accorde `USAGE` et `SELECT` uniquement sur les séquences d'identifiants des tables SOW IA `sowia_messages` et `sowia_memory_items`. L'ancien fichier racine `supabase_schema.sql` accordait ces privilèges sur toutes les séquences du schéma `public`. Si cet ancien script a déjà été exécuté dans un environnement existant, des droits plus larges peuvent donc subsister : le schéma courant ne révoque volontairement pas les droits sur les séquences d'autres applications.

Avant et après le script, dans le projet isolé uniquement, examiner les droits effectifs sur les séquences :

```sql
select n.nspname as schema_name,
       c.relname as sequence_name,
       pg_get_userbyid(c.relowner) as owner,
       has_sequence_privilege('anon', c.oid, 'USAGE') as anon_usage,
       has_sequence_privilege('authenticated', c.oid, 'USAGE') as authenticated_usage,
       has_sequence_privilege('authenticated', c.oid, 'SELECT') as authenticated_select
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where c.relkind = 'S'
  and n.nspname = 'public'
order by c.relname;
```

Après le script, les deux séquences SOW IA doivent être accessibles au rôle `authenticated` pour les insertions prévues. Les autres séquences ne doivent pas recevoir de privilèges applicatifs uniquement à cause de l'ancien script. Ne révoquer aucun droit sur une séquence tierce sans avoir identifié son propriétaire, son usage et les dépendances de l'application concernée ; préparer toute correction séparément dans le projet isolé.

---

## Compatibilité de la limite des notes mémoire

Effectuer le contrôle SQL ci-dessous **après** l'exécution de `supabase/schema.sql` dans le projet isolé. Dans un projet neuf, la table n'existe pas avant cette étape.

La mémoire standard accepte au plus 1 000 caractères, tandis que la mémoire étendue Premium accepte jusqu'à 5 000 caractères côté application. Le script `supabase/schema.sql` définit une contrainte de 5 000 caractères, mais `CREATE TABLE IF NOT EXISTS` ne modifie pas une table déjà créée avec une ancienne contrainte de 1 000 caractères.

Avant tout essai Premium dans le projet isolé, contrôler la contrainte réelle :

```sql
select conname, pg_get_constraintdef(oid) as definition
from pg_constraint
where conrelid = 'public.sowia_memory_items'::regclass
  and contype = 'c'
order by conname;
```

Résultat attendu : la contrainte sur `content` autorise au minimum 1 à 5 000 caractères. Si une contrainte existante plafonne à 1 000 caractères, ne pas la supprimer ni la remplacer automatiquement : documenter l'écart et préparer une migration dédiée, testée uniquement dans le projet isolé, après vérification des données et des usages. Aucun ajustement de contrainte ne doit être improvisé sur la base de production.



## Scénarios complémentaires — limiteur de requêtes partagé

> À exécuter uniquement après les contrôles précédents et dans le projet `SOW IA - TEST`. Ne jamais lancer cette migration dans le projet de production.

### Précontrôle et migration

1. Vérifier que le projet affiché est bien le projet isolé de test et relever son identifiant.
2. Contrôler en lecture seule l'existence éventuelle de `public.sowia_rate_limits`, ses politiques RLS et ses privilèges.
3. Examiner la fonction `public.sowia_consume_rate_limit(text)` si elle existe déjà : propriétaire, définition, `SECURITY DEFINER`, `search_path` et droits EXECUTE.
4. Si un objet existe avec une définition ou des privilèges inattendus, arrêter et analyser ; ne pas le remplacer automatiquement.
5. Dans ce projet isolé uniquement, appliquer `supabase/migrations/202611060001_shared_rate_limits.sql`.
6. Répéter les contrôles en lecture seule et confirmer : RLS activé, aucun accès direct à la table pour `anon` ou `authenticated`, exécution RPC accordée à `authenticated` uniquement (hors propriétaire de confiance), et aucun droit EXECUTE pour `PUBLIC` ou `anon`.

Requêtes de contrôle :

```sql
select n.nspname, c.relname, c.relrowsecurity, c.relforcerowsecurity
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public'
  and c.relname = 'sowia_rate_limits';

select schemaname, tablename, policyname, permissive, roles, cmd, qual, with_check
from pg_policies
where schemaname = 'public' and tablename = 'sowia_rate_limits';

select table_schema, table_name, grantee, privilege_type
from information_schema.role_table_grants
where table_schema = 'public' and table_name = 'sowia_rate_limits'
order by grantee, privilege_type;

select routine_schema, routine_name, security_type, routine_definition
from information_schema.routines
where routine_schema = 'public'
  and routine_name = 'sowia_consume_rate_limit';

select routine_schema, routine_name, grantee, privilege_type
from information_schema.routine_privileges
where routine_schema = 'public'
  and routine_name = 'sowia_consume_rate_limit'
order by grantee, privilege_type;
```

### Essais fonctionnels avec deux comptes

Utiliser les comptes A et B et deux sessions indépendantes. Effectuer les appels RPC avec les jetons de session normaux de chaque compte, jamais avec une clé service-role dans le navigateur.

| Test | Action | Résultat attendu |
|---|---|---|
| R1 | A consomme le quota Assistant jusqu'à 10 appels dans une fenêtre de 60 s | Les 10 premiers sont autorisés |
| R2 | A effectue un 11e appel Assistant dans la même fenêtre | Refusé, remaining = 0 |
| R3 | B consomme son quota Assistant pendant que A est limité | B dispose de son propre compteur |
| R4 | A utilise deux sessions/appareils avec le même compte | Les deux sessions partagent le compteur |
| R5 | Appeler la RPC sans session authentifiée | Refusé |
| R6 | Appeler la RPC avec une clé de compartiment inconnue | Refusé |
| R7 | A tente SELECT, INSERT, UPDATE ou DELETE directement sur la table | Refusé |
| R8 | Répéter des appels simultanés au-delà du seuil | Jamais plus que le seuil autorisé dans la fenêtre |
| R9 | Attendre l'expiration de la fenêtre puis appeler de nouveau | Nouveau compteur, première requête autorisée |
| R10 | Simuler une réponse RPC indisponible ou invalide côté application | Opération protégée refusée, aucun fallback local |
| R11 | Vérifier les autres catégories (PDF, Web, Premium et documents) | Chaque catégorie respecte sa fenêtre et son seuil définis côté SQL |

Pour R1 et R2, tester également les catégories ayant des limites différentes avec un jeu de test séparé. Pour R8, lancer plusieurs appels concurrents avec le même compte et noter le nombre exact d'autorisations. Conserver uniquement les résultats expurgés, sans jetons, identifiants personnels ni contenu de document.

### Critères supplémentaires de réussite

- Les compteurs sont isolés par utilisateur et catégorie, et partagés entre les sessions du même compte.
- Les appels concurrents sont atomiques et ne permettent pas de dépasser le seuil.
- Les utilisateurs authentifiés ne peuvent pas lire ou modifier directement la table.
- Seul le RPC contrôlé peut consommer un quota ; les limites ne sont jamais fournies par le client.
- Les erreurs RPC bloquent l'opération protégée et ne divulguent pas de détails internes.
- Les quotas sont bien distincts par catégorie et reviennent à zéro après expiration.
- Aucun de ces essais n'est réalisé sur la base de production.

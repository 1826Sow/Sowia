# FINAL TEC — conception du registre des rôles d'approbation

**Statut :** spécification de conception uniquement. Ce document n'est ni une migration, ni une implémentation, ni une autorisation de mise en production.

**Cible de travail :** branche `security/hardening-clean`, PR #276.  
**Principe :** aucune modification de `main`, aucune migration appliquée à Supabase et aucun secret ajouté.

## 1. Objectif et périmètre

Définir une source d'autorité versionnée pour déterminer qui peut approuver une opération FINAL TEC, à quel titre, pendant quelle période et selon quelle politique.

Le registre doit permettre de prouver qu'au moment de la finalisation :
- les deux approbateurs étaient authentifiés par un fournisseur OIDC explicitement approuvé ;
- chacun détenait un rôle d'approbation actif et non révoqué ;
- les deux identités étaient distinctes selon le couple immuable `(issuer, subject)` ;
- les décisions de rôle étaient suffisamment fraîches et liées à une version précise ;
- aucune révocation concurrente ne pouvait être ignorée silencieusement ;
- la consommation des deux défis applicatifs et l'écriture de l'audit/outbox étaient atomiques dans PostgreSQL.

Ce registre ne valide pas à lui seul un jeton OIDC, ne signe pas les approbations, ne fournit pas le stockage de clés, ne prouve pas l'ancrage externe et n'autorise aucun workload.

## 2. Autorité et séparation des responsabilités

### 2.1 Identité canonique

La clé d'identité est le couple `(issuer, subject)` après validation cryptographique OIDC. Un email, un nom d'affichage, un identifiant de profil modifiable ou un simple identifiant utilisateur local ne constitue pas une identité d'approbateur suffisante.

L'association entre l'identité OIDC et le compte SOWIA doit être établie côté serveur. Les données fournies par le navigateur ne peuvent ni créer cette association ni choisir le rôle.

### 2.2 Rôle dédié

Créer un rôle explicite, par exemple `security_approver`. Ne pas déduire ce rôle de :
- `app_metadata.role = admin` ;
- `app_metadata.sowia_admin` ;
- l'accès Premium ou Professionnel ;
- la propriété d'un compte, d'un plan ou d'une transaction ;
- un rôle GLOBAL Action Governance limité à un plan.

Les rôles d'administration fonctionnelle et les rôles d'approbation de sécurité restent séparés.

### 2.3 Gouvernance des attributions

Avant migration, le propriétaire du système doit désigner formellement :
1. l'autorité habilitée à accorder et révoquer `security_approver` ;
2. au moins deux personnes habilitées à administrer le registre, avec séparation des tâches ;
3. la procédure de vérification hors bande des identités ;
4. la procédure d'urgence permettant de suspendre immédiatement un approbateur ;
5. les exigences de conservation et d'audit des décisions d'attribution.

Aucun compte initial ne doit être automatiquement promu par une migration. Le registre démarre sans approbateur actif tant que les attributions ne sont pas approuvées et enregistrées explicitement.

## 3. Modèle logique proposé

Les noms ci-dessous sont des noms de conception. Ils ne préjugent pas des noms physiques retenus après revue SQL.

### 3.1 `final_tec_role_assignments`

Champs minimaux :
- `assignment_id` UUID, clé primaire générée côté serveur ;
- `issuer` et `subject`, identité OIDC canonique ;
- `role`, limité à une liste autorisée, dont `security_approver` ;
- `status`, limité à `active | suspended | revoked | expired` ;
- `valid_from`, `valid_until` ;
- `version`, entier strictement croissant pour chaque identité/rôle ;
- `granted_by`, `grant_reason_code`, `created_at` ;
- `revoked_by`, `revocation_reason_code`, `revoked_at` ;
- référence à l'événement d'audit correspondant.

Contraintes :
- `issuer`, `subject` et `role` non vides et bornés ;
- `valid_until` strictement postérieur à `valid_from`, si renseigné ;
- une seule attribution courante non terminale par identité et rôle ;
- les transitions de statut sont contrôlées par RPC, pas par UPDATE client ;
- les enregistrements historiques ne sont pas supprimés ni réécrits par les rôles applicatifs.

Une nouvelle attribution après révocation crée une nouvelle version ou un nouvel enregistrement lié à l'historique. Elle ne réactive pas silencieusement l'ancien enregistrement.

### 3.2 `final_tec_role_events`

Journal append-only des transitions :
- identifiant d'événement ;
- identité OIDC, rôle et identifiant d'attribution ;
- statut précédent et nouveau statut ;
- version précédente et nouvelle version ;
- acteur ayant demandé le changement ;
- motif codifié et référence de justification protégée, si nécessaire ;
- horodatage serveur ;
- digest de l'événement et identifiant de corrélation.

Les rôles `anon` et `authenticated` ne peuvent ni insérer, ni modifier, ni supprimer ces événements directement. Les événements ne doivent pas contenir de jeton, secret, nonce en clair ou donnée personnelle non nécessaire.

### 3.3 Décision de rôle liée à un défi

Chaque défi d'approbation FINAL TEC doit référencer :
- `issuer` et `subject` vérifiés ;
- le rôle requis ;
- `assignment_id` et `role_version` observés ;
- la version de politique ;
- l'identifiant d'opération et le digest de requête ;
- l'expiration et l'état de consommation.

Le défi ne doit jamais être créé à partir d'une déclaration de rôle fournie par le client.

## 4. API transactionnelle proposée

Les fonctions ci-dessous sont des contrats logiques, pas des RPC existantes.

### 4.1 Attribution

`final_tec_grant_role(identity, role, validity, reason, expected_registry_version)`

- Exécutable uniquement par l'autorité d'attribution approuvée.
- Vérifie la version attendue pour empêcher les mises à jour perdues.
- Vérifie les conflits de séparation des tâches.
- Insère l'attribution et l'événement d'audit dans une transaction unique.
- Refuse les doublons ou une attribution concurrente.
- Ne permet pas de s'auto-attribuer un rôle.

### 4.2 Suspension et révocation

`final_tec_revoke_role(assignment_id, reason, expected_version)`

- Verrouille l'attribution et vérifie la version.
- Passe l'attribution à un état terminal ou suspendu selon la décision explicite.
- Incrémente la version de rôle/revocation.
- Ajoute l'événement d'audit dans la même transaction.
- Refuse les appels rejoués ou fondés sur une version obsolète.
- Rend toute nouvelle approbation impossible dès le commit de révocation.

Une révocation concurrente avec une approbation doit être sérialisée sur la même ligne d'autorité. La transaction de finalisation relit/verrouille la version courante au moment du commit. Si la révocation gagne la course, l'approbation est refusée. Si l'approbation gagne, son ordre de sérialisation doit être démontrable et l'événement de révocation ultérieur reste visible.

### 4.3 Vérification et finalisation de la paire

`final_tec_authorize_approval_pair(operation_id, challenge_a, challenge_b, expected_policy_version)`

Dans une transaction unique :
1. verrouiller l'opération ;
2. verrouiller les deux défis dans un ordre déterministe ;
3. verrouiller les attributions de rôle dans un ordre déterministe ;
4. vérifier exactement deux sujets distincts (`issuer + subject`), deux défis, deux nonces et deux identifiants de clé distincts ;
5. vérifier statut actif, validité temporelle, version courante, absence de révocation et fraîcheur de l'authentification OIDC déjà validée côté serveur ;
6. vérifier le digest et la politique immuables ;
7. consommer les deux défis ou aucun ;
8. écrire l'événement d'audit et l'outbox dans la même transaction ;
9. retourner un succès strict uniquement après commit durable.

La fonction ne doit pas appeler un fournisseur OIDC, un KMS ou un service d'ancrage réseau à l'intérieur de la transaction. Ces vérifications externes sont faites par le backend avant la transaction, puis liées à des références et versions vérifiables.

## 5. Concurrence, révocation et fraîcheur

- Utiliser l'heure de la base de données pour les expirations.
- Verrouiller les lignes dans un ordre global constant : opération, défis triés, attributions triées, audit/outbox.
- Ajouter des contraintes uniques comme dernier rempart contre les courses.
- Rejeter toute version de rôle différente de la version courante.
- Ne jamais accepter un résultat de cache comme autorité finale lors du commit.
- Définir une politique mesurée de fraîcheur OIDC et de rôle ; la durée maximale de cache doit être bornée et documentée.
- Les changements de rôle, suspensions et révocations doivent être immédiatement visibles par les fonctions de finalisation via la même frontière transactionnelle.
- Les erreurs retournées au client sont des codes stables et expurgés ; les détails internes ne contiennent aucun secret.

## 6. Contrôles PostgreSQL et RLS

- Activer RLS sur toutes les tables du registre.
- Refuser tout accès direct d'écriture à `anon` et `authenticated`.
- Ne pas exposer la liste des approbateurs à tous les utilisateurs.
- Réserver les RPC à un rôle backend dédié, avec privilèges minimaux et `search_path` fixé.
- Éviter `SECURITY DEFINER` sauf nécessité démontrée ; si utilisé, contrôler explicitement l'appelant et les privilèges.
- Révoquer les droits par défaut hérités de `PUBLIC`.
- Ne pas utiliser la clé `service_role` dans le navigateur.
- Les administrateurs de l'application ne doivent pas pouvoir modifier silencieusement les événements historiques.
- Le journal PostgreSQL append-only ne doit pas être présenté comme inviolable contre un administrateur de base privilégié ; l'ancrage externe indépendant reste requis.

## 7. Tests d'acceptation obligatoires

### Tests fonctionnels et négatifs
- Attribution valide par une autorité autorisée.
- Refus d'auto-attribution et d'attribution par un utilisateur ordinaire.
- Refus d'un rôle `admin` utilisé comme substitut de `security_approver`.
- Refus d'une identité OIDC non liée ou d'un issuer non autorisé.
- Refus d'une attribution expirée, suspendue ou révoquée.
- Refus d'une version de rôle périmée.
- Refus de deux défis liés au même sujet, même si les libellés diffèrent.
- Refus de rejeu d'un défi ou d'un nonce.
- Refus de substitution de digest, de politique ou d'opération.
- Vérification qu'une erreur ou panne produit un refus fermé.

### Tests de concurrence
- Approbation et révocation simultanées du même rôle.
- Deux finalisations concurrentes tentant de consommer la même paire.
- Deux attributions concurrentes pour la même identité et le même rôle.
- Reprise après perte de connexion avant/après commit.
- Vérification qu'une transaction échouée ne consomme aucun défi et n'écrit aucun audit partiel.

Les tests doivent s'exécuter sur PostgreSQL/Supabase de test dédié avec au moins deux comptes distincts et des sessions séparées. Les tests unitaires avec fakes ne remplacent pas ces tests d'intégration.

## 8. Barrières avant migration

Aucune migration ne doit être créée ou appliquée avant :
1. approbation formelle du modèle de gouvernance des rôles ;
2. décision documentée sur l'autorité d'attribution et le nombre minimal d'administrateurs ;
3. revue SQL indépendante des contraintes, fonctions, RLS et privilèges ;
4. tests sur un projet Supabase dédié ;
5. vérification des courses révocation/finalisation ;
6. stratégie de sauvegarde, restauration et audit ;
7. confirmation que les environnements test, préproduction et production sont séparés.

Aucun approbateur par défaut ne sera inséré. Tant que les décisions et preuves ci-dessus manquent, FINAL TEC reste **NO-GO / NOT_RUN** et aucun workload ne peut être activé.

## 9. Décisions restant à formaliser

| Décision | État |
|---|---|
| Identité canonique `issuer + subject` | Principe retenu |
| Rôle dédié `security_approver` | Proposition à approuver |
| Autorité d'attribution/révocation | À désigner |
| Séparation des administrateurs du registre | À formaliser |
| Fraîcheur maximale OIDC et rôles | À définir avec le fournisseur |
| Politique de révocation d'urgence | À approuver |
| Schéma SQL physique et RPC | Non implémentés |
| Tests PostgreSQL multi-comptes | Non exécutés |
| Revue indépendante | Non obtenue |

**Conclusion :** ce document transforme les décisions d'architecture en exigences vérifiables, sans simuler une implémentation. La prochaine étape technique, après validation de la gouvernance et de la revue SQL, sera une migration isolée sur la branche de travail et testée exclusivement sur un projet Supabase dédié.

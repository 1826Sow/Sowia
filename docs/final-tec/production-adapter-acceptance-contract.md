# FINAL TEC — contrat d'acceptation des adaptateurs de production

**Statut :** spécification préparatoire uniquement — aucun fournisseur réel raccordé.

Ce document fixe les critères d'acceptation avant tout raccordement à un fournisseur d'identité, un coffre de clés ou un journal d'audit externe. Il ne sélectionne aucun fournisseur et ne contient aucun secret.

## 1. Principes non négociables

- Fail-closed : absence, indisponibilité, réponse ambiguë ou configuration partielle = refus.
- Aucune identité, aucun rôle, aucune clé et aucun statut de révocation ne sont déduits d'une donnée fournie par le demandeur.
- Aucun fallback vers un adaptateur de test, une clé locale ou SQLite en environnement de production.
- Les secrets ne sont jamais écrits dans les logs, traces, messages d'erreur, métriques ou artefacts CI.
- Aucun adaptateur de production ne peut émettre seul un état `execution_authorized`.
- Les environnements de test, préproduction et production utilisent des autorités, clés, audiences et stockages distincts.

## 2. Adaptateur d'identité OIDC

L'adaptateur ne sera accepté que s'il :

1. utilise un issuer HTTPS explicitement autorisé et une audience exacte, définis hors du jeton ;
2. valide la signature avec les clés obtenues depuis le JWKS associé à cet issuer, sans accepter d'algorithme non autorisé ni `alg=none` ;
3. contrôle `iss`, `aud`, `exp`, `iat`, `sub`, le nonce de session, `auth_time`, ainsi que les exigences ACR/AMR applicables ;
4. limite les redirections réseau, valide TLS et refuse les URL JWKS hors de l'origine attendue ;
5. gère la rotation JWKS avec une durée de cache bornée et un échec fermé lorsque la clé `kid` reste inconnue ;
6. obtient les rôles depuis une source d'autorité distincte du jeton utilisateur et vérifie leur validité au moment de l'approbation ;
7. permet révocation, désactivation de compte et retrait de rôle avec une latence maximale mesurée et documentée.

**Preuves requises :** configuration d'issuer/audience approuvée, tests de rotation et de révocation, preuves TLS, tests de rejeu de nonce, traces expurgées, et test négatif sur chaque claim obligatoire.

## 3. Adaptateur de signature et coffre de clés

- Les clés privées de signature sont générées et conservées dans un KMS/HSM ou un service équivalent avec contrôle d'accès dédié.
- Les clés privées ne sont jamais exportées vers l'application, les variables d'environnement, GitHub Actions ou les fichiers du dépôt.
- La signature est produite par une opération de signature distante authentifiée ; la vérification Ed25519 reste possible avec des clés publiques versionnées.
- Chaque clé possède un identifiant, un propriétaire, un usage, une période de validité et un statut (active, suspendue, révoquée, retirée).
- La rotation et la révocation sont testées ; les anciennes signatures ne deviennent pas automatiquement valides après une rotation.
- Dès qu'une clé est désactivée pour signer, la vérification échoue également par défaut : un champ `issued_at` signé ne constitue pas, à lui seul, un horodatage externe fiable permettant d'accepter une signature antidatée.
- Les deux approbateurs doivent être distincts et leur séparation est vérifiée par identifiants d'autorité stables, pas par simple différence de libellé.

**Preuves requises :** politique IAM minimale, journal des opérations de signature, test de refus d'un principal non autorisé, test de rotation, test de révocation et attestation de gestion des clés.

## 4. Registre anti-rejeu et audit durable

Le stockage de production doit fournir une primitive atomique unique qui, dans une transaction indivisible :

1. vérifie et consomme les deux nonces d'approbation ;
2. enregistre l'événement d'audit correspondant ;
3. lie l'événement à l'identifiant d'autorisation, au hash canonique de la demande, aux deux identités, aux deux identifiants de clés et aux empreintes des signatures ;
4. garantit l'idempotence et le refus d'une seconde consommation ;
5. ne retourne un succès qu'après confirmation durable du commit.

SQLite local est réservé aux tests et au développement mono-hôte. La production exige un stockage transactionnel partagé, une politique de sauvegarde/restauration vérifiée et un journal d'audit externe protégé contre la modification par les opérateurs applicatifs.

**Preuves requises :** tests concurrents multi-processus et multi-hôtes, panne avant/pendant/après commit, rollback intégral, restauration, idempotence, contrôle d'accès et détection de falsification.

## 5. Observabilité et exploitation

- Journaliser les identifiants de corrélation, décisions et codes d'échec, jamais les jetons, secrets, nonces en clair ou clés privées.
- Synchroniser les horloges et mesurer la dérive ; une dérive au-delà du seuil configuré bloque l'approbation.
- Émettre des alertes sur échecs OIDC/JWKS, refus de rôle, signatures invalides, conflits de nonce, rollback, indisponibilité du KMS et défaut d'audit.
- Définir les procédures de révocation d'urgence, rotation, restauration et réponse à incident.
- Les tableaux de bord investisseurs ne reçoivent que des agrégats non sensibles, publiés après validation, sans exposition d'identifiants, secrets ou événements opérationnels détaillés.

## 6. Barrière de mise en service

Aucun raccordement réel ni passage à G2-B n'est accepté avant :

- sélection et approbation explicites des fournisseurs ;
- environnement isolé et secrets provisionnés hors du dépôt ;
- tests d'intégration contre les environnements de test officiels des fournisseurs ;
- revue de sécurité indépendante des flux d'identité, de clés, de nonce et d'audit ;
- preuves de séparation des rôles, de révocation et de reprise après incident ;
- approbation formelle de la mise en service.

Tant que ces critères ne sont pas tous satisfaits, le résultat reste **NO-GO / NOT_RUN**. Ce contrat ne confère aucun droit d'exécution et n'active aucun workload.

## 7. Contrats d'interface avant intégration

Le module `final_tec_provider_contracts.py` formalise les interfaces attendues,
sans dépendance à un fournisseur : résolution JWKS, session d'approbation côté
serveur, annuaire de rôles courant, signature distante, vérification de signature
et registre partagé avec commit nonce/audit atomique et contrôle de santé.

Le contrôle local `validate_production_adapter_bundle` vérifie uniquement la
présence des six rôles d'adaptateur, leurs méthodes et une déclaration explicite
`production_grade = True`. Cette déclaration est une assertion de configuration,
pas une preuve de sécurité ni une certification. Le contrôle ne contacte aucun
fournisseur et ne valide ni TLS, ni IAM, ni KMS/HSM, ni transaction distribuée.

**Tests de contrat :** les fakes vérifient la structure et les refus en cas
d'adaptateur absent/incomplet/non déclaré. Ils ne constituent pas des tests
d'intégration fournisseur. L'adaptateur SQLite mono-hôte existant reste réservé
au développement et aux tests et ne satisfait pas ce contrat de registre partagé.

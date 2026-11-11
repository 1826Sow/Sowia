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
présence des sept rôles d'adaptateur, leurs méthodes et une déclaration explicite
`production_grade = True`. Cette déclaration est une assertion de configuration,
pas une preuve de sécurité ni une certification. Le contrôle ne contacte aucun
fournisseur et ne valide ni TLS, ni IAM, ni KMS/HSM, ni transaction distribuée.

Pour les sessions, `consume_approval_session(session_id, expected_nonce)` doit
réaliser une consommation atomique à usage unique dans le stockage serveur :
la vérification du nonce attendu et le passage de la session à l'état consommé
doivent être indivisibles, y compris sous appels concurrents. La méthode doit
retourner le booléen strict `True` uniquement pour l'unique consommation
réussie ; session absente, nonce différent, session expirée, déjà consommée
ou erreur de stockage doivent produire un refus. Une simple lecture suivie
d'une suppression non atomique ne satisfait pas ce contrat.

**Tests de contrat :** les fakes vérifient la structure et les refus en cas
d'adaptateur absent/incomplet/non déclaré. Ils ne constituent pas des tests
d'intégration fournisseur. L'adaptateur SQLite mono-hôte existant reste réservé
au développement et aux tests et ne satisfait pas ce contrat de registre partagé.

## 8. Banc de conformité des adaptateurs

Le module `final_tec_adapter_conformance.py` fournit un exécuteur de sondes
explicites. Chaque sonde doit vérifier un comportement de sécurité précis
(exemples : issuer invalide refusé, clé révoquée refusée, nonce déjà consommé
refusé, panne du registre traitée en échec fermé). Une sonde qui retourne autre
chose que le booléen strict `True`, ou qui lève une exception, fait échouer
l'ensemble de la suite. Les messages d'exception ne sont pas recopiés dans le
rapport afin d'éviter la fuite de données sensibles.

Les tests actuellement intégrés utilisent des sondes locales de démonstration.
Ils vérifient le comportement du harnais, **pas** un fournisseur réel. Pour
l'acceptation d'un adaptateur réel, les sondes devront être fournies et exécutées
contre les environnements officiels de test du fournisseur, avec preuves
expurgées, configuration contrôlée et revue indépendante. Une suite vide,
ambiguë ou incomplète ne peut pas être déclarée conforme.

## 9. Matrice minimale des sondes d'acceptation réelles

| Domaine | Cas positif | Cas négatif obligatoire | Preuve attendue |
|---|---|---|---|
| OIDC/JWKS | jeton valide, issuer/audience attendus | issuer/audience faux, `alg=none`, `kid` inconnu, signature invalide | résultat d'intégration expurgé et configuration approuvée |
| Session | nonce frais, session liée à l'approbation | nonce absent, différent ou rejoué ; session expirée | traces corrélées sans jeton ni nonce en clair |
| Autorisations | rôle actif relu au moment de l'approbation | rôle retiré, compte désactivé, approbateur non autorisé | preuve de lecture de l'annuaire et délai de révocation mesuré |
| KMS/HSM | principal autorisé signe avec clé attendue | principal non autorisé, clé suspendue/révoquée, coffre indisponible | journal de signature et politique IAM expurgés |
| Anti-rejeu/audit | deux nonces distincts consommés et audit durable dans le même commit | nonce déjà consommé, commit interrompu, audit indisponible, concurrence sur même autorisation | résultats multi-processus/multi-hôtes et preuve de rollback |
| Exploitation | restauration testée et alertes reçues | dérive d'horloge, perte de connectivité, tentative de falsification | rapport de reprise, alertes et horodatages contrôlés |

Chaque cas doit être exécuté contre un environnement de test officiel ou une
infrastructure représentative approuvée. Les cas concurrents doivent inclure
plusieurs processus et plusieurs hôtes. Les résultats doivent préciser la
version de l'adaptateur, la version de configuration, l'environnement, l'heure
UTC et l'identifiant de corrélation, sans inclure de secret ni donnée personnelle.

La réussite d'un sous-ensemble ne permet pas de déclarer le domaine complet
conforme. Toute sonde obligatoire absente, non exécutée ou non vérifiable
maintient le domaine en **NOT_RUN** et bloque G2-B.


## 10. Ancrage externe indépendant des checkpoints d'audit

L'interface distincte ExternalAuditAnchor formalise le futur raccordement d'un journal externe indépendant du stockage SQLite applicatif. Elle expose append_checkpoint et verify_checkpoint. Un checkpoint lie au minimum le numéro de séquence, le hash précédent, le hash de l'événement et son horodatage UTC ; le reçu externe doit être conservé et vérifiable.

Le contrôle local validate_external_audit_anchor vérifie uniquement les deux méthodes et l'assertion production_grade = True, sans exécuter de code de l'adaptateur. Il ne contacte aucun service et ne valide ni l'indépendance administrative, ni la rétention WORM, ni l'horodatage, ni l'authenticité du reçu. Les tests avec fakes sont structurels, pas des preuves d'ancrage externe.

Critères d'acceptation d'un fournisseur réel : identité et contrôle d'accès distincts de l'administration SQLite ; rétention verrouillée WORM ou équivalent ; reçu externe authentifiable lié au checkpoint ; refus fermé si écriture, vérification ou reçu échoue ; tests de suppression, réécriture, troncature, rejeu, panne, reprise et restauration ; preuves expurgées et revue indépendante.

Limite actuelle : le coordinateur et l'outbox SQLite sont implémentés dans le dépôt, mais aucun fournisseur externe réel n'est sélectionné, raccordé ou appelé ; aucun reçu externe réel n'est donc émis. Le hash-chain SQLite ne protège pas contre un administrateur privilégié capable de réécrire ou tronquer toute la base. L'ancrage externe reste NOT_RUN et G2-B reste NO-GO / NOT_RUN.


## 11. Coordination fail-closed avec outbox transactionnel

Le module `final_tec_audit_anchor.py` formalise le coordinateur entre le
registre transactionnel et l'ancre externe. Le registre doit fournir
`commit_pair_audit_and_outbox` : consommation des deux nonces, append de
l'événement d'audit et création du checkpoint en attente dans **une seule
transaction locale**. Le checkpoint est ensuite envoyé à l'ancre externe,
son reçu est vérifié, puis le registre marque durablement le checkpoint comme
ancré. Le callback ne retourne `True` qu'après ces quatre étapes.

La reprise après panne doit être idempotente : pour un même identifiant
d'autorisation et un même événement, le registre retourne le checkpoint
d'outbox déjà créé, sans reconsommer les nonces. L'ancre externe doit accepter
une répétition strictement identique comme la même opération et refuser toute
réutilisation conflictuelle de la séquence. Une panne après écriture externe
mais avant le marquage local est récupérée par append idempotent, vérification
du reçu, puis marquage local.

**Important :** il ne s'agit pas d'une transaction distribuée atomique entre
SQLite et le fournisseur. Le statut d'approbation reste en attente/échec fermé
jusqu'à confirmation externe durable. Les fakes de test vérifient seulement le
contrat du coordinateur ; aucun adaptateur SQLite outbox ni fournisseur réel
n'est encore implémenté ou raccordé. G2-B reste **NO-GO / NOT_RUN**.


## 12. Implémentation SQLite de l'outbox et reprise

Le registre `SQLiteAtomicApprovalStore` expose désormais
`commit_pair_audit_and_outbox`. La consommation des deux nonces, l'insertion
de l'événement d'audit et la création de la ligne `pending` dans
`dual_approval_anchor_outbox` sont exécutées sous le même
`BEGIN IMMEDIATE` et validées par un seul commit SQLite. Une erreur à
l'insertion de l'outbox annule donc aussi les consommations et l'audit.

L'identifiant d'autorisation est unique dans l'outbox. Une reprise avec les
mêmes empreintes de nonces et le même événement canonique retourne le
checkpoint existant sans reconsommer les nonces. Toute tentative de réutiliser
cet identifiant avec un événement ou une paire de nonces différente échoue.
Le reçu est enregistré par une transition à sens unique `pending -> anchored`,
et les champs d'identité du checkpoint ne peuvent pas être modifiés via les
opérations normales SQLite.

Le coordinateur expose `recover_pending()` : après redémarrage, il lit les
checkpoints en attente, répète l'append idempotent auprès de l'ancre, vérifie
le reçu puis marque le checkpoint comme ancré. Si le fournisseur reste
indisponible ou si la vérification échoue, le checkpoint reste en attente et
la fonction ne signale aucune récupération réussie.

Les tests ajoutés couvrent l'atomicité de l'insertion outbox, la reprise
exacte, les réutilisations conflictuelles, la transition du reçu, et la
récupération après redémarrage avec le registre SQLite réel. Ils ne remplacent
pas les tests d'intégration du fournisseur externe, ni une revue de la
résistance aux administrateurs privilégiés.


## 13. Vérification indépendante de l'outbox

`SQLiteAtomicApprovalStore.verify_anchor_outbox()` relie chaque ligne outbox
à sa ligne d'audit par séquence et contrôle l'égalité des champs
`previous_hash`, `event_hash`, `created_at` et `event_json`. Il vérifie
également la canonicalisation RFC 8785 de l'événement et du reçu, la forme des
deux empreintes de nonce et la cohérence entre statut et reçu.

Les tests couvrent l'état pending, l'état anchored, la détection d'une
altération directe de la base et douze tentatives concurrentes idempotentes
pour une même autorisation. Ces contrôles détectent des incohérences ; ils ne
constituent pas une preuve cryptographique externe ni une défense contre un
administrateur privilégié réécrivant l'ensemble de la base.


## 14. Raccordement obligatoire du moteur d'approbation

Le moteur `validate_dual_approval` accepte un callback atomique injecté.
Pour le parcours avec ancrage externe, le callback à injecter est
`ExternalAuditAnchorCoordinator(ledger, anchor).callback()`. Il ne retourne
`True` qu'après l'écriture transactionnelle du checkpoint, l'append externe,
la vérification du reçu et le marquage durable `anchored`.

La méthode historique `SQLiteAtomicApprovalStore.atomic_commit_callback`
reste disponible uniquement pour les scénarios offline/local : elle réalise
l'audit SQLite, mais **ne garantit pas l'ancrage externe**. Son docstring
l'indique explicitement. Elle ne doit pas être utilisée pour déclarer une
approbation G2-B de production.

Un test d'intégration relie maintenant le moteur réel de double approbation,
le registre SQLite, le coordinateur et une ancre de test. Il vérifie que le
moteur n'accepte le callback qu'après ancrage confirmé. Le fournisseur de test
ne constitue pas une preuve d'intégration à un service externe réel.


## 15. Preuve de reprise après réouverture SQLite

Un test ferme le chemin de l'ancien processus (objets store et coordinateur détruits),
réouvre le même fichier SQLite avec une nouvelle instance, vérifie que le checkpoint
est toujours `pending`, puis lance `recover_pending()` avec une ancre disponible.
Le test vérifie l'état final `anchored`, l'unicité de l'audit, l'intégrité de la
chaîne et de l'outbox, ainsi que la réutilisation du checkpoint exact sans nouvelle
consommation de nonces.

Cette preuve est couverte par la suite automatisée exécutée avec succès dans
GitHub Actions sur le commit `bb0ea5212b577d91c0ff18cbb27a8b4fa6978641`
(run SOW IA quality checks #2675, le 11 novembre 2026). Elle confirme le
scénario de reprise SQLite simulé par le test ; elle ne constitue pas une
preuve d'intégration fournisseur externe ni une revue indépendante.


## 16. Adaptateur JWKS HTTPS local — limites et tests

Le module `final_tec_jwks.py` ajoute un résolveur HTTP(S) générique destiné
à être injecté dans `OIDCApprovalIdentityVerifier`. Il exige une URL JWKS
HTTPS dont l'origine figure explicitement dans une liste d'autorisation
configurée hors du jeton. Le transport standard valide les certificats TLS ;
toutes les redirections sont refusées. Les réponses sont limitées en taille,
le délai réseau et la durée de cache sont bornés, les clés RSA de signature
RS256 sont filtrées, les identifiants `kid` dupliqués font échouer le
chargement et un `kid` inconnu déclenche au plus un rafraîchissement avant
échec fermé.

Les tests locaux couvrent les URL ambiguës/non HTTPS, l'origine non autorisée,
les réponses non JSON, les redirections, les réponses surdimensionnées, les
identifiants dupliqués, le cache borné, le rafraîchissement après rotation et
le refus d'un `kid` toujours inconnu. Ils utilisent un faux transport et des
clés RSA générées pour les tests : ils ne constituent pas une preuve TLS
contre un fournisseur réel, ne sélectionnent aucun issuer, ne découvrent pas
automatiquement les métadonnées OIDC et ne prouvent pas la politique JWKS
d'un fournisseur. L'origine autorisée, l'URL JWKS, les audiences, l'ACR/AMR
et les rôles doivent être approuvés et provisionnés séparément.

La CI FINAL TEC exécute désormais `tests/test_final_tec_jwks.py`. Tant que
l'adaptateur n'a pas été raccordé à un issuer réel approuvé et testé dans son
environnement officiel, le contrôle OIDC/JWKS de production reste
**NOT_RUN** et G2-B reste **NO-GO / NOT_RUN**.


## 17. Séparation entre connexion SOW IA et approbation FINAL TEC

Le parcours de connexion actuel de l'application SOW IA utilise GitHub OAuth
via Supabase Auth et PKCE. Il sert à authentifier une session applicative.
L'identifiant de navigateur utilisé pour retrouver le vérificateur PKCE est
un identifiant de portée, pas un justificatif d'identité ni un facteur
d'authentification.

Cette session applicative **n'est pas une preuve d'approbation FINAL TEC**.
Elle ne doit jamais être convertie directement en approbation, ni servir à
fabriquer les claims OIDC `acr`, `amr`, `auth_time` ou le nonce attendu.
En particulier, un retour OAuth GitHub ne prouve pas à lui seul une
authentification résistante à l'hameçonnage ni l'utilisation de WebAuthn.

Le vérificateur FINAL TEC continue d'exiger un jeton provenant d'un issuer
OIDC explicitement configuré, une audience exacte, une session d'approbation
côté serveur, un nonce frais, un `auth_time` récent, l'`acr` approuvé et
l'`amr` requis. La clé de signature doit être résolue par la source JWKS
configurée et le rôle doit être relu dans l'annuaire d'autorité au moment de
chaque approbation. Aucun fallback vers la session Streamlit/Supabase n'est
autorisé si l'un de ces éléments manque ou si un fournisseur est indisponible.

**Décision d'intégration actuelle :** conserver GitHub/Supabase pour la
connexion générale de SOW IA ; laisser l'autorité OIDC d'approbation séparée
et non configurée tant qu'un fournisseur offrant les claims et facteurs
exigés n'a pas été choisi et vérifié. Ne pas assouplir `required_acr` ou
`required_amr` pour faire passer le parcours OAuth existant.

**Preuves de blocage ajoutées :** un test de régression vérifie explicitement
qu'un jeton dont le seul `amr` est `oauth` est refusé par le vérificateur
FINAL TEC. Ce test utilise des clés et un jeton générés localement ; il prouve
le refus du code, pas la configuration d'un fournisseur réel.

## 18. Registre de preuves et séquence de levée des blocages

Ce registre distingue les contrôles de code déjà automatisés des preuves
d'infrastructure et d'exploitation qui ne peuvent pas être déduites d'une CI
sur fakes. Les statuts ci-dessous décrivent l'état connu de la branche au
11 novembre 2026 ; ils ne valent pas attestation externe.

### 18.1 Statuts normalisés

- **PASS_LOCAL** : test automatisé local/CI réussi ; portée limitée au code et
  aux dépendances effectivement testés.
- **NOT_CONFIGURED** : fournisseur ou infrastructure non sélectionné(e) ou
  non raccordé(e).
- **NOT_RUN** : preuve réelle requise mais non exécutée ou non fournie.
- **BLOCKED_REVIEW** : preuve technique éventuellement disponible, mais
  validation indépendante obligatoire absente.
- **ACCEPTED** : preuve vérifiée, versionnée, attribuée à un environnement
  identifié et approuvée selon le processus de revue. Ce statut ne peut pas
  être attribué par une simple déclaration production_grade.

### 18.2 État des preuves à la date de référence

| Contrôle | État connu | Ce qui est effectivement prouvé | Preuve manquante pour ACCEPTED |
|---|---|---|---|
| Vérificateur OIDC et séparation OAuth applicatif | PASS_LOCAL | Tests locaux, dont le refus d'un jeton amr=oauth seul | Issuer approuvé, claims ACR/AMR réels, tests d'intégration officiels |
| Résolution JWKS et logique de rotation | PASS_LOCAL | Tests avec faux transport, clés générées et scénarios de rotation simulés | TLS réel, issuer/JWKS autorisés, rotation et révocation chez le fournisseur |
| Session d'approbation côté serveur | NOT_CONFIGURED | Interface contractuelle seulement | Adaptateur réel, stockage sécurisé, expiration, liaison nonce/session, tests de panne |
| Annuaire de rôles courant | NOT_CONFIGURED | Interface contractuelle seulement | Source d'autorité, retrait de rôle/compte et mesure de latence |
| Signature distante KMS/HSM | NOT_CONFIGURED | Interfaces et contrôles locaux seulement | Service réel, IAM minimal, journaux, rotation et révocation testées |
| Registre partagé multi-hôtes | NOT_CONFIGURED | SQLite local, atomicité/outbox/reprise et concurrence locale testées | Adaptateur transactionnel partagé, tests multi-hôtes, sauvegarde/restauration |
| Ancre externe WORM | NOT_CONFIGURED | Coordinateur et tests avec ancre simulée | Service indépendant, reçus vérifiables, rétention verrouillée et tests d'altération |
| RLS Supabase avec deux comptes réels | NOT_RUN | Aucun résultat de test réel dans le workflow PR | Exécution contrôlée avec deux comptes distincts et preuves expurgées |
| Revue de sécurité indépendante | BLOCKED_REVIEW | Aucun avis indépendant enregistré sur la PR | Revue par une personne/équipe distincte, avec décision et périmètre consignés |
| Autorisation G2-B | NO-GO / NOT_RUN | Aucun workload exécuté ni déploiement autorisé | Tous les contrôles obligatoires ACCEPTED et approbation formelle |

### 18.3 Ordre de levée des blocages

1. **Décision d'identité** : sélectionner explicitement un fournisseur OIDC
   capable de satisfaire les exigences d'authentification forte, d'ACR/AMR,
   de fraîcheur et de révocation. Documenter issuer, audience et politique
   de claims approuvés. Ne pas modifier les exigences pour s'adapter à un
   fournisseur insuffisant.
2. **Identité et autorisations** : intégrer l'issuer/JWKS dans un environnement
   de test isolé, puis la session d'approbation serveur et l'annuaire de rôles.
   Exécuter les cas positifs et négatifs, y compris révocation et rejeu.
3. **Clés et audit** : raccorder le KMS/HSM, le registre transactionnel partagé
   et l'ancre WORM indépendante. Démontrer les contrôles IAM, l'atomicité
   locale requise, l'idempotence, la reprise et les refus fermés.
4. **Validation de plateforme** : exécuter les tests RLS avec deux comptes
   réels, puis les tests multi-processus/multi-hôtes, de restauration et
   d'incident dans l'environnement représentatif approuvé.
5. **Revue indépendante** : faire examiner les configurations, les preuves,
   les scénarios d'abus et les limites résiduelles par une personne ou équipe
   distincte de l'implémentation. Consigner les constats et leur résolution.
6. **Décision G2-B** : seulement après acceptation de chaque ligne obligatoire,
   soumettre une décision formelle distincte. La réussite CI seule ne déclenche
   jamais cette décision.

### 18.4 Format minimal de chaque preuve

Chaque dossier de preuve doit contenir : identifiant unique, contrôle couvert,
résultat attendu et observé, statut, SHA du code testé, version/configuration
de l'adaptateur, environnement et fournisseur, horodatage UTC, identifiant de
corrélation, opérateur/exécutant, lien vers le rapport expurgé et décision du
relecteur indépendant lorsqu'elle est requise. Aucun jeton, secret, nonce en
clair, clé privée ni donnée personnelle ne doit être joint au registre.

Une preuve expirée après changement de code, de configuration, de fournisseur
ou de politique doit être réexécutée. Les preuves PASS_LOCAL ne sont jamais
promues automatiquement en ACCEPTED.

**Décision conservatoire :** au vu des statuts ci-dessus, FINAL TEC demeure
**NO-GO / NOT_RUN** pour G2-B. Ce registre ne configure aucun fournisseur,
ne crée aucun secret, ne lance aucun workload et n'autorise ni fusion ni
déploiement.

## 19. Matrice d'acceptation du registre partagé et de l'ancre WORM

Cette matrice définit les essais obligatoires avant tout raccordement de production. Elle ne désigne aucun fournisseur et ne constitue pas une preuve d'infrastructure réelle.

### 19.1 Registre transactionnel partagé multi-hôtes

| ID | Scénario | Résultat exigé | Preuve |
|---|---|---|---|
| LEDGER-01 | Deux hôtes consomment simultanément la même paire de nonces | Un seul commit gagnant ; aucun audit en double | Test concurrent multi-processus et multi-hôtes |
| LEDGER-02 | Même authorization_id avec charges différentes | Refus du conflit, aucune substitution de charge | Test de collision et empreintes persistées |
| LEDGER-03 | Panne à chaque frontière du commit | Aucun nonce partiellement consommé ni état partiel | Injection de panne et inspection transactionnelle |
| LEDGER-04 | Perte de connexion pendant un commit au résultat ambigu | Réconciliation idempotente, aucune double consommation | Coupure réseau et reprise par identifiant stable |
| LEDGER-05 | Bascule primaire/réplica pendant une approbation | Aucun split-brain ni acquittement non durable | Failover réel, preuve de quorum et de fencing |
| LEDGER-06 | Redémarrage d'un nœud avec outbox pending | Reprise du checkpoint exact, sans rejouer les nonces | Test multi-hôtes et corrélation des identifiants |
| LEDGER-07 | Restauration d'une sauvegarde | Détection du rollback, des séquences perdues et des checkpoints déjà ancrés | Exercice de restauration et rapport d'intégrité |
| LEDGER-08 | Saturation, timeout ou indisponibilité du stockage | Refus fermé, aucun fallback SQLite local | Tests de panne et journaux expurgés |
| LEDGER-09 | Révocation de rôle pendant une course | Règle de fraîcheur explicitée et respectée | Test concurrent révocation/approbation |
| LEDGER-10 | Échec d'écriture audit/outbox | Rollback complet de la transaction locale | Injection d'erreur DB et inspection |

Le contrat réel devra préciser isolation transactionnelle, cohérence, quorum,
durabilité des acquittements, fencing des anciens primaires, limites de retry
et traitement des commits dont la réponse réseau est ambiguë. Une base
éventuellement cohérente ne satisfait pas automatiquement l'exigence d'unicité
atomique.

### 19.2 Ancre externe WORM indépendante

| ID | Scénario | Résultat exigé | Preuve |
|---|---|---|---|
| WORM-01 | Append valide | Reçu vérifiable lié à la séquence et aux hashes exacts | Reçu et spécification de vérification |
| WORM-02 | Rejeu du même append après timeout | Résultat idempotent, aucun doublon contradictoire | Test de déduplication fournisseur |
| WORM-03 | Reçu falsifié ou lié à un autre hash | Refus ; outbox reste pending | Tests de falsification |
| WORM-04 | Modification/suppression après verrouillage | Refus effectif, y compris pour l'administrateur ordinaire | Test WORM et configuration de rétention |
| WORM-05 | Raccourcissement/suspension de rétention | Détection et alerte bloquante | Test IAM et journal d'audit |
| WORM-06 | Panne ou timeout fournisseur | Aucun succès ; checkpoint pending récupérable | Injection de panne et reprise |
| WORM-07 | Append distant réussi mais réponse perdue | Recherche par clé idempotente avant nouvel append | Test timeout après acceptation |
| WORM-08 | Rupture de chaîne ou séquence dupliquée | Refus et alerte ; jamais anchored | Tests négatifs de chaîne |
| WORM-09 | Compromission du compte applicatif | Ce compte ne peut supprimer ni raccourcir la rétention | Matrice IAM et tests négatifs |
| WORM-10 | Export et vérification par un tiers | Vérification hors bande sans secret applicatif | Rapport indépendant reproductible |

L'ancre doit être administrativement et techniquement indépendante du registre.
Le compte applicatif d'écriture ne doit pas pouvoir modifier la rétention ni
supprimer les objets verrouillés. Les rôles d'administration de rétention
doivent être distincts et contrôlés.

### 19.3 Sémantique de cohérence

Le registre et l'ancre ne forment pas une transaction distribuée unique.
Le modèle admis est : transaction locale atomique (nonces + audit + outbox
pending), append externe idempotent, vérification indépendante du reçu, puis
marquage durable anchored.

États autorisés :
- **pending** : transaction locale validée, preuve externe non confirmée.
- **anchored** : reçu vérifié pour le checkpoint exact et marquage durable confirmé.
- **blocked** : incohérence ou preuve invalide ; aucune approbation positive.
- **reconciliation_required** : résultat distant ambigu ; rechercher le reçu
  avec l'identifiant idempotent avant tout nouvel append.

Une approbation positive exige l'état anchored lorsque l'ancrage externe est
obligatoire. Les retries sont bornés, observables et conservent le tuple exact.
Aucun fallback vers SQLite mono-hôte n'est permis en production.

### 19.4 Critères de sortie et preuves

Pour chaque ID, conserver le résultat positif et négatif, le SHA exact, la
version du schéma, la configuration effective, l'environnement, les
corrélations, les horodatages UTC, les rapports expurgés, les métriques de
reprise et la décision du relecteur. Exclure secrets, jetons, nonces en clair
et clés privées.

La sortie exige cumulativement : essais LEDGER et WORM réussis dans un
environnement représentatif ; exercices de panne, failover et restauration ;
garanties de cohérence/durabilité documentées ; IAM vérifié ; ancre réellement
indépendante avec rétention verrouillée ; preuves examinées indépendamment.

**État actuel :** interfaces et simulations locales seulement. Aucun registre
partagé multi-hôtes ni service WORM réel n'est raccordé. Tous les essais
d'infrastructure de cette section restent **NOT_CONFIGURED / NOT_RUN**.
Cette matrice ne modifie pas le statut G2-B.

# FINAL TEC — audit de cohérence des contrats G0 à G2-B

## Décision

**NO-GO maintenu pour toute exécution G2-B.** Cet audit est documentaire et
compare les contrats existants. Il ne modifie aucun code exécutable, ne lance
aucun processus et ne constitue pas une autorisation.

Périmètre examiné :
- G0 : `final_tec_runner_policy.py` — validation locale du manifeste et transitions ;
- G1 : `final_tec_offline_fixtures.py` — évaluation de fixtures synthétiques ;
- G2-A : `final_tec_g2_policy.py` — validation statique du profil d'isolation ;
- G2-B : protocole #246, revue sécurité #247 et registre #248.

## 1. Résumé des constats

| ID | Constat | Risque / conséquence | Priorité |
|---|---|---|---|
| C-01 | G2-B exige un nonce à usage unique, mais le manifeste G0 ne définit aucun champ nonce ni registre de consommation | Le caractère à usage unique n'est pas garanti par le contrat G0 actuel | Critique avant toute exécution |
| C-02 | G2-B exige une autorisation écrite et une identité de réviseur, mais G0 ne vérifie que des champs déclaratifs comme authorization_status et approval_ref | Une chaîne « approved » ne prouve ni signature, ni identité, ni approbation réelle | Critique avant toute exécution |
| C-03 | G0 ne lie pas explicitement le manifeste à un hôte, une version runtime, un digest d'image et une empreinte de profil G2-A | Risque de substitution de l'environnement après approbation | Critique avant toute exécution |
| C-04 | G2-A valide des paramètres déclarés, sans attester leur application effective ; cette limite est correctement annoncée mais doit rester visible dans tous les états | Risque de confondre validation statique et confinement réel | Critique de présentation et de gouvernance |
| C-05 | G0 définit emergency_stop comme un booléen qui doit être false pour valider le manifeste, alors que G2-B décrit un arrêt d'urgence opérationnel, indépendant et vérifié | Le sens du champ est ambigu : signal d'arrêt actif ou présence d'un mécanisme d'arrêt | Élevée |
| C-06 | G0 autorise la transition prepared vers running après validation locale ; cette transition ne prouve pas que les préconditions hôte/runtime de G2-B ont été vérifiées | Une machine d'état applicative ne doit pas être interprétée comme un feu vert d'exécution système | Critique avant toute exécution |
| C-07 | Le statut G1 est bien synthétique, pending/draft et sans workload ; il ne constitue pas un contrôle d'exécution G2-B | Risque de surinterprétation des tests CI G1 | Faible, garder l'avertissement |
| C-08 | Le registre #248 exige une séparation collecteur/réviseur/approbateur, mais aucune identité ni signature de ces rôles n'est actuellement vérifiée par G0 | Contrôle de gouvernance documentaire, pas encore mécanisme technique | Élevée |

## 2. Détails et preuves de lecture

### G0 — autorisation locale

Le manifeste G0 actuel exige notamment run_id, approval_ref, operator_id,
resource_id, authorization_status, expires_at, network_enabled, budget_limit,
estimated_cost, currency, cost_basis, plafonds et emergency_stop.

Le code exige authorization_status égal à approved et vérifie une expiration
timezone-aware. Il valide les formats, limites, devise et coût. Cependant, le
module indique lui-même que l'appelant doit encore obtenir une autorisation
indépendante. Le contrat actuel ne vérifie pas de signature cryptographique,
d'identité d'approbateur, de nonce consommable, ni de liaison cryptographique
entre l'approbation et l'environnement exact.

### G1 — fixtures hors ligne

G1 appelle le validateur G0, exige la ressource locale sandbox, un coût estimé nul,
le cost_basis local_fixture et des plafonds serrés. Il retourne explicitement
workload_executed=false, network_used=false, provider_contacted=false et des
résultats pending/draft. Il s'agit d'une validation de données synthétiques fixes,
pas d'une exécution de processus ni d'une mesure matérielle.

### G2-A — profil statique

G2-A vérifie la forme et les valeurs déclarées du profil rootless, namespaces,
filesystem, sécurité, réseau et ressources. Le résultat précise
static_profile_validated_not_enforced, execution_permitted=false,
runtime_started=false et host_controls_verified=false. Aucun contrôle hôte
n'est effectué. Cette distinction est correcte et doit être préservée.

### G2-B — protocole

Le protocole G2-B réclame un nonce à usage unique, une autorisation spécifique,
une vérification des contrôles réellement actifs, un runtime et une image épinglés,
un arrêt indépendant et une preuve de nettoyage. Ces exigences sont plus fortes
que les champs et garanties techniques du contrat G0 actuel. C'est un écart de
contrat à résoudre avant tout développement d'un exécuteur.

## 3. Contrat cible à définir avant tout exécuteur

Un futur contrat G0/G2-B devrait au minimum lier, dans une autorisation immuable :

1. run_id et nonce aléatoire à usage unique, avec expiration et consommation atomique ;
2. identifiant d'autorisation, émetteur, approbateur, opérateur et réviseur ;
3. preuve vérifiable de l'approbation et portée exacte de cette approbation ;
4. identifiant d'hôte/environnement, OS/kernel et runtime/version ;
5. digest exact de l'image et empreinte du profil G2-A ;
6. scénario fixe autorisé, durée, limites CPU/mémoire/PID/I/O/output/scratch ;
7. politique réseau, politique secrets/montages et exigences de journalisation ;
8. identifiant et disponibilité du contrôleur d'arrêt indépendant ;
9. états et transitions explicites, avec expiration, révocation et anti-rejeu ;
10. décision de revue indépendante et lien vers les preuves.

Ce contrat devra distinguer :
- `emergency_stop_available` : mécanisme d'arrêt configuré et contrôlé ;
- `stop_requested` : demande d'arrêt effectivement reçue ;
- `execution_blocked` : verrou fail-closed ;
- `execution_authorized` : autorisation valide, sans pour autant prouver les contrôles hôte ;
- `host_controls_verified` : contrôles actifs observés par une méthode indépendante.

Le champ booléen actuel `emergency_stop` ne doit pas être réinterprété sans
migration et tests dédiés. La transition `prepared -> running` ne devra jamais
être considérée comme autorisée par la seule validation de manifeste.

## 4. Ordre recommandé de remédiation

| Ordre | Action future | Type | Condition de sortie |
|---|---|---|---|
| 1 | Spécifier le schéma d'autorisation signé, le nonce et l'anti-rejeu | Contrat/documentation | Schéma approuvé et cas de rejet documentés |
| 2 | Spécifier le binding hôte/runtime/image/profil au run_id | Contrat/documentation | Aucun champ critique mutable après approbation |
| 3 | Clarifier les états emergency-stop et les transitions | Contrat/documentation | Table de transitions non ambiguë |
| 4 | Ajouter tests unitaires de contrat et cas négatifs, sur branche isolée | Code local/CI uniquement | Tests ciblés réussis ; aucun accès hôte |
| 5 | Faire une revue indépendante du nouveau contrat | Gouvernance | Décision écrite |
| 6 | Revoir les preuves hôte/runtime effectives via le registre #248 | Revue documentaire | Toutes les preuves critiques examinées |
| 7 | Décision distincte sur une éventuelle exécution G2-B | Autorisation séparée | Périmètre précis et approbation explicite |

Aucune étape ne doit sauter directement de G0/G1/G2-A à l'exécution.

## 5. Interdictions maintenues

Cet audit n'autorise pas :
- changement du code de production ou de la branche main ;
- fusion, déploiement ou activation d'un exécuteur ;
- installation ou lancement d'un runtime/conteneur/VM ;
- modification du système hôte, cgroups, namespaces, firewall, seccomp ou LSM ;
- connexion réseau, fournisseur, Internet, Supabase ou secrets ;
- benchmark, provisioning, paiement ou dépense ;
- changement de statut d'une preuve vers verified/published.

## Conclusion

Les étapes G0, G1 et G2-A sont des validations locales/documentaires de portée
limitée. Elles ne forment pas encore une chaîne d'autorisation technique complète
pour G2-B. Les écarts C-01 à C-06 doivent être résolus dans un contrat dédié,
puis testés hors production et revus indépendamment. Le statut reste
**NO-GO / NOT_RUN**.

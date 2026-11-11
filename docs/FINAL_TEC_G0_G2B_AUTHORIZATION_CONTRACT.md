# FINAL TEC — contrat cible d'autorisation G0–G2-B

## 1. Statut et portée

**Spécification documentaire uniquement — NO-GO / NOT_RUN.**

Ce document définit le contrat cible à implémenter et à tester hors production
avant tout exécuteur G2-B. Il ne modifie pas le validateur G0 existant et ne
l'autorise pas à lancer un processus.

Dépendances de conception :
- PR #249 : audit des écarts G0 à G2-B ;
- PR #246 : protocole de smoke test ;
- PR #247 : revue de sécurité et arrêt d'urgence ;
- PR #248 : registre des preuves indépendantes.

Le validateur G0 actuel reste un validateur local de manifeste. Le statut
`authorization_status=approved` est déclaratif et ne constitue pas une preuve
cryptographique d'approbation. Le présent contrat ne doit pas être considéré comme
implémenté tant qu'un code séparé, des tests négatifs et une revue indépendante
n'auront pas été réalisés.

## 2. Principes non négociables

1. **Fail-closed** : champ absent, inconnu, expiré, invalide ou incohérent = refus.
2. **Autorisation liée au contexte** : une approbation vaut uniquement pour le run,
   l'opérateur, l'hôte, le runtime, l'image, le profil et le scénario explicitement
   désignés.
3. **Immutabilité après signature** : toute modification d'un champ couvert invalide
   la signature et impose une nouvelle approbation.
4. **Anti-rejeu** : un nonce aléatoire n'est accepté qu'une fois, avec consommation
   atomique côté service d'autorisation.
5. **Séparation des rôles** : demandeur, approbateur, opérateur et réviseur ne sont
   pas interchangeables ; aucune auto-approbation.
6. **Séparation autorisation / preuve technique** : une signature valide ne prouve
   pas que les contrôles de l'hôte sont actifs.
7. **Aucun démarrage implicite** : validation du manifeste et transition d'état ne
   valent jamais, seules, autorisation d'exécuter.
8. **Aucune auto-publication** : toute preuve demeure pending/draft jusqu'à une
   revue distincte.

## 3. Enveloppe d'autorisation proposée

L'objet logique comporte quatre blocs. Les champs sont obligatoires sauf mention
explicite contraire.

### A. Identité et cycle de vie

| Champ | Type / contrainte | Finalité |
|---|---|---|
| schema_version | chaîne versionnée | Évolution contrôlée du contrat |
| authorization_id | identifiant unique | Référence de l'approbation |
| run_id | identifiant unique | Liaison au run exact |
| nonce | valeur aléatoire cryptographiquement sûre | Anti-rejeu |
| issued_at | date ISO 8601 avec fuseau | Début de validité |
| expires_at | date ISO 8601 avec fuseau | Fin de validité courte |
| revoked_at | date ou null | Révocation |
| status | draft, submitted, approved, revoked, consumed, expired, rejected | Cycle de vie |
| scenario_id | identifiant d'un scénario fixe autorisé | Empêche la substitution du workload |

Le nonce doit être généré par un composant de confiance, avoir une entropie
cryptographique suffisante et ne jamais être réutilisé. Sa consommation doit être
atomique : deux demandes concurrentes portant le même nonce ne peuvent pas toutes
deux réussir. Un stockage uniquement en mémoire ou un simple booléen dans le
manifeste ne suffit pas à garantir cette propriété entre processus ou redémarrages.

### B. Acteurs et approbation

| Champ | Type / contrainte | Finalité |
|---|---|---|
| requester_id | identité stable | Personne ou service demandeur |
| approver_id | identité stable, distincte du demandeur | Approbateur habilité |
| operator_id | identité stable | Opérateur du test |
| reviewer_id | identité stable, distincte de l'opérateur | Réviseur indépendant |
| approver_role | rôle issu d'une source d'identité autoritative | Vérifier l'habilitation |
| approval_policy_id | version de la politique appliquée | Reproductibilité |
| approval_signature | signature cryptographique sur le contenu canonique | Intégrité et attribution |
| signing_key_id | identifiant de clé publique attendue | Vérification et rotation |
| approval_evidence_ref | référence vers la preuve d'approbation conservée en privé | Audit |

La signature doit couvrir l'ensemble des champs d'autorisation, y compris les
limites, le scénario, les références de preuves et les identifiants d'environnement.
La représentation signée doit être canonique, versionnée et non ambiguë. Une
signature asymétrique telle qu'Ed25519 peut être évaluée lors de l'implémentation ;
l'algorithme, la bibliothèque, la rotation/révocation des clés et la protection de
la clé privée devront être validés par revue de sécurité avant adoption.

Ne jamais stocker de clé privée dans le dépôt, le manifeste, les journaux ou le
client. Le vérificateur utilise une clé publique de confiance et refuse les
algorithmes ou versions non autorisés.

### C. Liaison exacte à l'environnement

| Champ | Type / contrainte | Finalité |
|---|---|---|
| host_id | identifiant stable de l'hôte dédié | Éviter la substitution de machine |
| host_os | système et version | Contexte d'exécution |
| kernel_version | version exacte | Liaison au noyau examiné |
| architecture | architecture matérielle | Éviter les écarts de plateforme |
| runtime_name | runtime approuvé | Périmètre du moteur |
| runtime_version | version exacte | Éviter les changements silencieux |
| runtime_config_digest | SHA-256 de la configuration effective expurgée | Liaison de configuration |
| image_digest | digest immuable SHA-256 | Empêcher le remplacement de l'image |
| g2a_profile_digest | SHA-256 du profil G2-A approuvé | Liaison au profil contrôlé |
| evidence_bundle_ref | référence privée au dossier #248 | Associer les preuves examinées |

Les valeurs doivent être relevées ou confirmées par une source indépendante du
manifeste soumis. Une valeur auto-déclarée par l'opérateur ne suffit pas. Toute
différence entre valeur autorisée et valeur observée bloque le run.

### D. Scénario et limites

| Champ | Type / contrainte | Finalité |
|---|---|---|
| workload_digest | empreinte du scénario fixe | Interdire toute substitution |
| network_policy | deny_all pour G2-B initial | Pas de réseau |
| secrets_policy | none | Aucun secret injecté |
| mounts_policy_digest | empreinte de la liste de montages permise | Aucun montage non prévu |
| cpu_limit | valeur bornée | Limite CPU |
| memory_limit_bytes | entier borné | Limite mémoire |
| pids_limit | entier borné | Limite de processus |
| io_limit | valeur bornée et unité | Limite I/O |
| scratch_limit_bytes | entier borné | Espace temporaire |
| output_limit_bytes | entier borné | Taille de sortie |
| timeout_seconds | entier court et borné | Durée maximale |
| budget_limit | valeur et devise | Plafond financier, initialement nul pour le smoke test local |
| stop_controller_id | identifiant du contrôleur indépendant | Arrêt d'urgence |
| stop_policy_version | version de la politique d'arrêt | Reproductibilité |

Les limites ne peuvent pas être augmentées par le runtime après signature. Toute
augmentation exige une nouvelle autorisation et une nouvelle revue.

## 4. Vérification et consommation

Le futur service d'autorisation doit appliquer les contrôles dans cet ordre :

1. Vérifier la version de schéma et refuser les champs inconnus.
2. Vérifier la signature avec une clé publique de confiance et une politique
   cryptographique autorisée.
3. Vérifier l'identité et les rôles auprès d'une source d'identité fiable.
4. Vérifier la séparation requester/approver/operator/reviewer et l'absence
   d'auto-approbation.
5. Vérifier issued_at, expires_at, révocation et dérive d'horloge admissible.
6. Vérifier que le nonce est connu, non consommé et associé à cette autorisation.
7. Comparer l'hôte, le noyau, le runtime, l'image et le profil observés aux valeurs
   signées.
8. Vérifier le dossier de preuves et la décision indépendante, sans transformer
   automatiquement les preuves en verified.
9. Vérifier les limites, politiques réseau/secrets/montages et le contrôleur d'arrêt.
10. Consommer atomiquement le nonce juste avant la porte de lancement ; en cas
    d'échec ou d'incertitude, refuser et ne pas démarrer.

Le système doit résister aux courses concurrentes, aux redémarrages, aux rejeux,
aux expirations, aux révocations et aux réponses partielles du stockage. Une
indisponibilité du service d'identité, du stockage de nonce, du vérificateur de
signature ou du contrôleur d'arrêt impose un refus.

## 5. États et transitions cibles

La machine d'état G0 actuelle contient notamment `prepared -> running`. Cette
transition existante ne doit pas être interprétée comme une preuve de contrôles
hôte. La cible proposée ajoute des barrières distinctes :

| État | Sens | Transition suivante permise |
|---|---|---|
| draft | Demande en préparation | submitted, rejected |
| submitted | Demande soumise | approved, rejected |
| approved | Approbation signée et valide | preflight |
| preflight | Contrôles de contexte en cours | ready, rejected, aborted, expired |
| ready | Autorisation, preuves et contrôles effectifs revus | launch_permitted, aborted, expired |
| launch_permitted | Porte unique ouverte après consommation du nonce | running, aborted |
| running | Processus autorisé en cours | completed, aborted, timed_out, failed |
| completed | Processus terminé | pending_review |
| pending_review | Résultat privé en attente de revue | état terminal de revue séparé |
| rejected / aborted / expired / failed | États terminaux de refus ou d'échec | aucune reprise du même nonce |

La transition vers `launch_permitted` doit être protégée par un verrou atomique
et une décision de tous les contrôles obligatoires. Aucun état terminal ne peut
être réactivé avec le même nonce. Un nouvel essai exige un nouveau run_id, un
nouveau nonce et une nouvelle approbation.

## 6. Contrat d'arrêt d'urgence

Séparer les champs suivants, sans réutiliser le booléen G0 actuel :

- `emergency_stop_available` : le contrôleur indépendant est configuré et joignable ;
- `stop_requested` : demande d'arrêt reçue pour le run_id ;
- `stop_reason` : motif normalisé ;
- `stop_started_at` : horodatage ;
- `stop_completed_at` : horodatage uniquement après observation ;
- `process_group_empty` : constaté par le contrôleur ;
- `runtime_destroyed` : constaté par une source indépendante ;
- `cleanup_confirmed` : constaté et enregistré ;
- `restart_disabled` : politique effective confirmée.

Le contrôleur doit être hors du cycle de vie du workload et capable de terminer
tout le groupe de processus/cgroup. Si la fin du groupe ou le nettoyage ne peut
pas être observé, le statut devient `failed_cleanup_unconfirmed`, le run reste
bloqué et aucun redémarrage/retry n'est permis.

## 7. Compatibilité et migration

- Ne pas renommer ni réinterpréter immédiatement `emergency_stop` dans G0.
- Ne pas ajouter ces champs au manifeste existant sans versionner le schéma.
- Introduire un nouveau validateur de contrat versionné et séparé, puis tester la
  compatibilité explicitement.
- Le validateur actuel continue à produire `locally_validated_not_executed`,
  `pending` et `draft`.
- Aucun ancien manifeste ne doit être automatiquement promu vers le nouveau
  contrat.
- Aucun changement de branche `main`, migration de base, secret ou déploiement
  n'est inclus dans cette spécification.

## 8. Tests négatifs obligatoires avant toute revue GO

Les futurs tests isolés devront démontrer le refus en cas de :

1. signature absente, invalide, expirée ou utilisant un algorithme interdit ;
2. approbateur inconnu, rôle insuffisant ou auto-approbation ;
3. modification d'un seul champ après signature ;
4. nonce inconnu, déjà consommé, révoqué, expiré ou rejoué concurremment ;
5. run_id, hôte, noyau, runtime, version, image ou profil différents ;
6. scénario, limite, politique réseau ou politique secrets modifiés ;
7. preuve obligatoire manquante, périmée ou non examinée ;
8. contrôleur d'arrêt absent, inaccessible ou non indépendant ;
9. stockage, horloge, service d'identité ou vérificateur indisponible ;
10. tentative de relancer un état terminal ou de réutiliser le même nonce ;
11. tentative de transition directe de prepared vers running ;
12. nettoyage ou terminaison du groupe non confirmé.

Les tests doivent utiliser des clés et identités fictives, un stockage éphémère de
test et des fixtures locales. Ils ne doivent pas contacter de service externe ni
lancer de runtime/conteneur.

## 9. Conditions d'acceptation de la spécification

Avant de coder :
- revue du schéma par sécurité et architecture ;
- validation des rôles et de la source d'identité ;
- décision sur le mécanisme de signature et la gestion des clés ;
- décision sur le stockage transactionnel du nonce et de la révocation ;
- approbation des transitions et de la porte de lancement ;
- revue de compatibilité avec le G0 actuel.

Après implémentation isolée :
- tous les tests négatifs passent ;
- aucune voie de contournement vers running ;
- aucune dépendance à un état local non persistant pour l'anti-rejeu ;
- revue indépendante du code et des résultats CI ;
- aucune intégration hôte avant autorisation distincte.

## 10. Interdictions et conclusion

Cette spécification n'autorise pas :
- modification de G0, G1, G2-A ou de la branche main ;
- implémentation ou activation d'un exécuteur ;
- installation ou lancement d'un runtime, conteneur, VM ou processus ;
- accès à une machine, réseau, fournisseur, Internet, Supabase ou secret ;
- génération ou stockage d'une clé privée réelle ;
- benchmark, provisioning, paiement ou dépense ;
- publication de métriques ou promotion de preuves.

**Décision initiale : NO-GO / NOT_RUN.** Le contrat cible est spécifié pour
préparer une implémentation locale et testable. Les garanties ne sont pas encore
présentes dans le code G0 et aucune exécution G2-B n'est autorisée.

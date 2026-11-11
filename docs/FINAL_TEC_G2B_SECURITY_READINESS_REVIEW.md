# FINAL TEC — revue de préparation sécurité G2-B

## Décision actuelle

**NO-GO pour toute exécution réelle à ce stade.**

Cette revue documentaire complète le protocole G2-B. Elle ne constitue ni une
autorisation d'exécution, ni une validation d'un hôte, d'un runtime ou d'un
environnement de production. Aucun runtime n'a été choisi ou testé.

Dépendances :
- G0 : politique d'autorisation fail-closed ;
- G1 : fixtures synthétiques, tests CI ciblés réussis ;
- G2-A : validateur statique de profil, tests CI ciblés réussis ;
- G2-B : protocole documentaire de smoke test, PR #246.

Les validations CI précédentes portent sur du code de politique et des tests
unitaires. Elles ne démontrent pas que les contrôles du système d'exploitation sont
actifs ou correctement configurés.

## 1. Revue des conditions d'exécution

| Domaine | Condition de passage | Preuve exigée | Décision actuelle |
|---|---|---|---|
| Hôte | Hôte dédié/jetable, non-production, propriétaire et périmètre identifiés | Fiche hôte, version OS/kernel, approbation écrite | Non vérifié |
| Runtime | Runtime rootless et version exacte choisis, maintenus et approuvés | Version binaire, provenance, configuration exportée | Non choisi |
| Image | Image minimale, immuable, digest SHA-256 vérifié | Référence, digest recalculé, provenance/SBOM | Non choisie |
| Identité | UID/GID non-root, aucun privilège hérité | Configuration effective et identité observée depuis le workload | Non vérifié |
| Namespaces | User, PID, mount et network isolés réellement | Inspection depuis l'hôte et depuis l'environnement | Non vérifié |
| Filesystem | Racine read-only ; seul scratch borné inscriptible ; aucun montage sensible | Liste effective des montages et test d'écriture contrôlé | Non vérifié |
| Secrets | Aucun secret, socket runtime, agent SSH, credential cloud ou device exposé | Inventaire des variables, mounts, sockets et devices | Non vérifié |
| Sécurité Linux | no_new_privileges, capacités supprimées, seccomp et AppArmor/SELinux actifs | Configuration effective et empreintes des profils | Non vérifié |
| Réseau | Aucun lien/route utilisable, DNS et egress bloqués au niveau runtime et hôte | État interfaces/routes et règles de filtrage, vérifiés indépendamment | Non vérifié |
| Ressources | CPU, RAM, PID, I/O, scratch, output et durée appliqués par l'hôte | Paramètres cgroups v2 et compteurs observés pendant le test | Non vérifié |
| Journalisation | Logs minimaux, horodatés, protégés contre modification accidentelle | Échantillon expurgé et procédure de conservation | Non vérifié |
| Nettoyage | Environnement et descendants disparus, scratch nettoyé selon politique | État cgroup/runtime avant/après et rapport de nettoyage | Non vérifié |

Un champ déclaré dans le manifeste ou accepté par G2-A n'est pas une preuve de
configuration effective. Toute ligne sans preuve vérifiable bloque le lancement.

## 2. Revue du mécanisme d'arrêt d'urgence

Le mécanisme doit être indépendant du processus testé. Un signal envoyé uniquement au
processus principal n'est pas suffisant : les descendants doivent aussi être arrêtés.

### Contrat d'arrêt obligatoire

1. Un opérateur autorisé ou un contrôleur externe au workload déclenche un arrêt
   identifié par le run ID.
2. Le contrôleur marque immédiatement le run comme stop_requested, consomme ou
   révoque le nonce et bloque toute nouvelle transition vers running.
3. Le contrôleur demande la terminaison de l'ensemble du cgroup ou de l'environnement
   jetable, et non du seul PID principal.
4. Une courte période de grâce, strictement bornée, peut permettre une terminaison
   propre ; à son expiration, le contrôleur force la terminaison de tout le groupe.
5. Le contrôleur vérifie que le cgroup ne contient plus de processus et que le runtime
   ne signale plus d'environnement actif.
6. Le contrôleur empêche redémarrage automatique, retry, reprise de file ou
   réutilisation du nonce.
7. Le run est classé aborted ; si l'arrêt ou le nettoyage ne peut pas être prouvé,
   il est classé failed_cleanup_unconfirmed et reste bloqué.
8. Un événement d'audit consigne le motif, les horodatages, l'opérateur/contrôleur,
   les actions effectuées et le résultat des vérifications.

### Défaillances qui imposent un NO-GO

- Le contrôleur d'arrêt partage le même cycle de vie que le workload.
- Il ne peut pas terminer les descendants ou le cgroup complet.
- Le contrôleur ou le runtime devient inaccessible et l'état final ne peut être prouvé.
- Un redémarrage ou retry peut se produire après l'arrêt.
- Le nonce ou l'autorisation reste réutilisable.
- L'état de nettoyage est inconnu ou contradictoire.
- L'horloge, les journaux ou l'identité de l'opérateur ne permettent pas de reconstituer
  l'événement.

Aucun système ne doit prétendre que l'arrêt a réussi si l'état final n'a pas été
observé. En cas de doute, l'environnement reste isolé et le run est bloqué pour
intervention manuelle.

## 3. Plan de vérification préalable — sans exécution pour le moment

Avant toute autorisation G2-B, un réviseur indépendant devra examiner :

- le propriétaire et l'isolation de l'hôte ;
- les versions exactes du noyau et du runtime ;
- la provenance de l'image et les profils seccomp/AppArmor/SELinux ;
- les contrôles réseau au niveau de l'hôte ;
- les contrôleurs de ressources et leurs limites effectives ;
- l'indépendance et le comportement du mécanisme d'arrêt ;
- les journaux, la conservation et la preuve de nettoyage ;
- la procédure de retour arrière et de gestion d'incident.

La revue devra aboutir à une liste de preuves attachées, à des écarts identifiés et à
une décision signée GO ou NO-GO. Un GO documentaire n'est pas l'autorisation
d'exécuter : l'autorisation d'exécution G2-B doit être donnée séparément, avec hôte,
périmètre, durée, limites et responsable explicitement désignés.

## 4. Ordre des essais si autorisés ultérieurement

1. Vérifier les configurations effectives sans workload.
2. Tester le mécanisme d'arrêt sur un processus inoffensif fixe, isolé, à durée courte.
3. Vérifier la terminaison du groupe complet, l'absence de redémarrage et la révocation
   du nonce.
4. Vérifier le nettoyage et les preuves.
5. Seulement après revue du résultat d'arrêt, envisager le scénario nominal G2-B.

L'essai d'arrêt doit précéder le scénario nominal. Il doit être réalisé dans un
environnement jetable sans données utiles. Si un résultat d'arrêt ne peut être
confirmé, aucun scénario nominal ne démarre.

## 5. Limites et interdictions

Cette revue n'autorise pas :
- installation ou changement d'un runtime ou d'un logiciel hôte ;
- commande Docker/Podman, création de conteneur, VM ou namespace ;
- modification de cgroups, firewall, AppArmor, SELinux ou seccomp ;
- lancement de processus de test, même inoffensif ;
- accès réseau, fournisseur, Internet, Supabase ou secrets ;
- benchmark matériel, test hostile, test d'évasion ou scan ;
- provisioning, paiement ou dépense ;
- publication d'une preuve comme verified ou published.

## Conclusion

Le protocole G2-B est suffisamment cadré pour une revue de préparation, mais les
conditions effectives d'exécution, le runtime, l'hôte, les règles réseau et l'arrêt
d'urgence restent non vérifiés. La décision reste donc NO-GO / not_run.

Prochaine porte : revue indépendante des éléments techniques réels et décision
explicite de l'utilisateur sur un environnement et un périmètre précis. Aucun
lancement ne doit être déduit de la validation de ce document.

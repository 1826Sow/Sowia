# FINAL TEC — registre de preuves et fiche de revue indépendante G2-B

## Statut et règle de décision

**État initial : NO-GO / NOT_RUN.** Ce document est un formulaire de gouvernance
et de collecte de preuves. Il ne collecte aucune donnée depuis un hôte, ne lance
aucun test et n'autorise aucune exécution.

Il complète :
- PR #246 — protocole de smoke test local G2-B ;
- PR #247 — revue de préparation sécurité et mécanisme d'arrêt.

Une preuve ne peut être marquée « vérifiée » que si le réviseur indépendant a
examiné la source, la date, le périmètre et l'intégrité du document ou de la mesure.
Une déclaration de configuration, une capture isolée ou un test CI de code ne
prouve pas à elle seule l'état effectif de l'hôte.

## 1. États normalisés

| État | Signification |
|---|---|
| not_provided | Aucun élément remis |
| provided_unreviewed | Élément reçu, pas encore contrôlé |
| reviewed_pass | Source, périmètre et résultat contrôlés par le réviseur |
| reviewed_fail | Contrôle échoué ou preuve contradictoire |
| not_applicable | Hors périmètre, justification obligatoire |
| blocked | Contrôle impossible ou dépendance manquante |

Les statuts verified et published sont interdits dans cette fiche. Les éléments
restent privés et en brouillon jusqu'à une décision distincte de gouvernance.

## 2. Registre des preuves obligatoires

Pour chaque ligne, renseigner un identifiant unique, le propriétaire de la preuve,
la source exacte, l'horodatage avec fuseau, le périmètre, l'empreinte SHA-256 du
fichier remis, l'identité du collecteur et celle du réviseur indépendant. Ne jamais
joindre de secret, jeton, clé privée, mot de passe ou donnée personnelle inutile.

| ID | Domaine | Élément minimal à fournir | État initial |
|---|---|---|---|
| E-01 | Autorisation | Autorisation écrite, périmètre, durée, responsable, réviseur, limites et procédure d'arrêt | not_provided |
| E-02 | Propriété de l'hôte | Confirmation du propriétaire et preuve que l'environnement est dédié/jetable et non-production | not_provided |
| E-03 | Système | OS, version du noyau, architecture, configuration pertinente expurgée | not_provided |
| E-04 | Runtime | Nom, version exacte, provenance, mode rootless et configuration effective expurgée | not_provided |
| E-05 | Image | Référence immuable, digest SHA-256 recalculé, provenance et SBOM si disponible | not_provided |
| E-06 | Identité | UID/GID effectifs, absence de privilèges et identité du processus observée | not_provided |
| E-07 | Namespaces | Éléments démontrant l'isolation effective user/PID/mount/network | not_provided |
| E-08 | Filesystem | Montages effectifs, racine read-only, scratch plafonné, absence de montages hôte | not_provided |
| E-09 | Secrets et périphériques | Inventaire expurgé démontrant l'absence de secrets, sockets, agents, credentials et devices | not_provided |
| E-10 | Contrôles Linux | État effectif no_new_privileges, capabilities, seccomp et AppArmor/SELinux | not_provided |
| E-11 | Réseau | État effectif interfaces/routes, règles hôte et runtime, DNS et egress bloqués | not_provided |
| E-12 | Ressources | Limites cgroups v2 et compteurs effectifs CPU, mémoire, PID, I/O, output et durée | not_provided |
| E-13 | Arrêt d'urgence | Architecture indépendante, commande de contrôle, délai borné et preuve de terminaison du groupe complet | not_provided |
| E-14 | Anti-redémarrage | Paramètres effectifs empêchant restart, retry, reprise de file et réutilisation du nonce | not_provided |
| E-15 | Nettoyage | Procédure et preuve que cgroup, processus descendants, environnement et scratch sont nettoyés | not_provided |
| E-16 | Journalisation | Exemple expurgé de journal, horodatage, intégrité, conservation et contrôle d'accès | not_provided |
| E-17 | Incident/retour arrière | Procédure d'incident, responsable, seuil d'escalade et retour à un état sûr | not_provided |

## 3. Fiche de contrôle par preuve

À dupliquer pour chaque preuve :

- Identifiant :
- Domaine :
- Propriétaire / collecteur :
- Source exacte et méthode de collecte :
- Date et heure avec fuseau :
- Hôte / runtime / version / périmètre concernés :
- Nom du fichier remis (expurgé) :
- Empreinte SHA-256 recalculée par le réviseur :
- Limites de la preuve :
- Résultat du contrôle :
- État normalisé :
- Commentaire et écart :
- Réviseur indépendant :
- Date de revue :

Le réviseur doit pouvoir reproduire le calcul d'empreinte sur le fichier remis.
Une empreinte ne prouve pas l'authenticité de la source, l'identité de l'auteur,
l'exécution réelle ou l'exactitude d'une mesure.

## 4. Indépendance et séparation des rôles

- Le collecteur ne peut pas être l'unique approbateur de sa propre preuve.
- Le réviseur doit être distinct de l'opérateur qui exécuterait ultérieurement le test.
- L'approbateur de l'autorisation doit être explicitement identifié.
- Toute dérogation doit être écrite, justifiée et approuvée ; aucune dérogation
  n'est permise pour l'absence d'autorisation, l'accès réseau interdit, les secrets
  exposés ou l'échec de l'arrêt/nettoyage.
- Les éléments bruts restent dans un espace privé à accès limité. La fiche ne doit
  contenir que des références et des métadonnées expurgées.

## 5. Décision de revue indépendante

La décision globale est NO_GO si :
- une preuve obligatoire manque, est périmée, non vérifiable ou contradictoire ;
- le périmètre ou la propriété de l'hôte n'est pas clair ;
- le runtime, l'image ou la configuration effective ne correspondent pas ;
- un contrôle réseau, secret, filesystem ou ressource n'est pas prouvé ;
- l'arrêt d'urgence ne peut pas terminer tous les descendants ;
- l'absence de redémarrage et le nettoyage complet ne sont pas démontrés ;
- les rôles collecteur/réviseur/approbateur ne sont pas séparés.

### Résultat

- Décision : NO_GO (valeur initiale obligatoire)
- Preuves reviewed_pass :
- Preuves reviewed_fail :
- Preuves blocked :
- Écarts ouverts :
- Mesures correctives requises :
- Réviseur indépendant :
- Approbateur :
- Date et heure avec fuseau :
- Référence de l'autorisation distincte, si elle existe :

Un résultat GO de revue ne vaut pas autorisation de lancement. L'exécution
G2-B nécessite encore une autorisation explicite distincte, liée à un hôte, une
durée, un scénario fixe, des limites et un opérateur précis.

## 6. Barrière avant toute exécution

Aucun lancement n'est permis tant que les conditions suivantes ne sont pas toutes
réunies et contrôlées :

1. Les preuves E-01 à E-17 sont examinées ou déclarées non applicables avec
   justification approuvée.
2. Tous les contrôles critiques sont reviewed_pass.
3. Le réviseur indépendant a signé une décision de revue.
4. L'autorisation distincte précise l'hôte, le runtime, l'image, le scénario, les
   limites, la fenêtre temporelle, l'opérateur et l'arrêt d'urgence.
5. Le mécanisme d'arrêt a été vérifié avant le scénario nominal.
6. Un contrôle final confirme que les conditions n'ont pas changé depuis la revue.

Tout changement d'hôte, de noyau, de runtime, de version, de digest, de profil de
sécurité ou de règles réseau invalide les preuves concernées et impose une nouvelle
revue.

## 7. Interdictions

Ce registre n'autorise ni collecte automatique, ni connexion à une machine, ni
installation, ni lancement de processus, ni commande Docker/Podman, ni changement
de firewall/cgroups/LSM, ni accès à Internet/Supabase/fournisseur, ni provisionnement,
ni dépense, ni publication de métriques ou de preuves.

**Conclusion initiale :** aucun dossier de preuves effectives n'a été fourni ou
examiné dans cette étape. Le statut reste NO_GO / NOT_RUN.

# FINAL TEC — protocole d'approbation à deux personnes

## 1. Objet et statut
Ce document définit un protocole de contrôle à deux personnes pour les
autorisations sensibles de FINAL TEC. Il complète la frontière de confiance
identité/approbation de la PR #255.

Statut : spécification préparatoire uniquement. Aucun compte, fournisseur
d'identité, service de signature, KMS/HSM, registre de production ou workload
n'est configuré. G2-B reste **NO-GO / NOT_RUN**.

## 2. Principe de séparation
Une action sensible ne peut pas être autorisée par une seule personne, même si
cette personne détient plusieurs rôles. Le système doit imposer des identités
distinctes et vérifier leur statut et leurs rôles au moment de chaque décision.

Rôles minimaux :
- **Requester** : soumet le besoin et le périmètre.
- **Approver A** : effectue la première approbation indépendante.
- **Approver B** : confirme séparément la même empreinte de demande.
- **Operator** : exécute une opération uniquement après autorisation valide.
- **Reviewer** : examine les preuves après opération et ne peut pas être
  l'operator.
- **Security administrator** : gère les clés et politiques ; ne peut pas
  approuver sa propre modification de politique ou de clés.

Pour une autorisation critique, Approver A et Approver B doivent être deux
sujets distincts, avec deux sessions d'identité distinctes et deux facteurs
d'authentification indépendants selon la politique retenue. L'auto-approbation
est interdite. Une personne ne peut pas satisfaire les deux approbations en
changeant simplement de session.

## 3. Objet exact soumis à approbation
Le service serveur construit une empreinte de demande à partir d'un objet
canonique RFC 8785 comprenant au minimum :
- authorization_id et run_id ;
- requester_id et les sujets d'approbation attendus ;
- scénario, objectif et classification de risque ;
- environnement cible et empreintes runtime/image/profil/workload ;
- limites réseau, secrets, CPU, mémoire, processus, I/O, stockage, sortie,
  durée et budget ;
- politique d'arrêt d'urgence et version de politique ;
- dates d'émission et d'expiration ;
- version du schéma et de la politique d'approbation.

Les deux approbations doivent viser exactement la même empreinte. Toute
modification d'un champ, même une limite plus restrictive, invalide les deux
approbations et impose une nouvelle demande. Le serveur ne doit pas accepter
une empreinte fournie uniquement par le client.

## 4. Séquence normative
1. Le requester soumet une demande ; elle reçoit l'état `pending_approval`.
2. Le serveur valide la structure, les limites, l'environnement déclaré et la
   politique applicable, puis calcule l'empreinte canonique.
3. Le serveur authentifie Approver A via le fournisseur d'identité et vérifie
   l'affectation actuelle du rôle. A examine le périmètre complet et signe
   l'empreinte avec sa clé autorisée.
4. Le serveur enregistre A comme `approved`, sans autoriser l'exécution.
5. Approver B se connecte séparément, réauthentifie son identité et son rôle,
   examine la même demande et confirme explicitement la même empreinte.
6. Le serveur vérifie que A et B sont deux sujets distincts, que les deux
   signatures sont valides, que les clés sont actives et que la politique
   n'a pas changé. Il passe alors à `approved_pending_execution_gate`.
7. Juste avant toute opération, un service indépendant revalide l'expiration,
   la révocation, les rôles, l'environnement réel, les limites, le nonce et
   l'arrêt d'urgence.
8. L'opérateur autorisé ne peut agir que si toutes les preuves exigées sont
   présentes et valides. Le protocole d'approbation seul ne lance aucun
   workload et ne démontre pas l'isolation de l'hôte.
9. Le reviewer examine les résultats et les preuves, sans pouvoir modifier
   rétroactivement la demande approuvée.

## 5. États et transitions
- `draft` → `pending_approval` : demande structurée soumise.
- `pending_approval` → `one_approval_recorded` : une approbation valide.
- `one_approval_recorded` → `approved_pending_execution_gate` : deuxième
  approbation distincte valide sur la même empreinte.
- Tout état non terminal → `rejected` : rejet explicite.
- Tout état non terminal → `revoked` : révocation autorisée.
- Tout état en attente → `expired` : échéance atteinte.
- Toute modification de demande → nouvelle version et retour à
  `pending_approval`; les signatures précédentes ne sont pas réutilisables.
- Toute incohérence d'identité, de signature, de clé, d'empreinte, de nonce,
  d'environnement ou de politique → `blocked`.

Aucun état ne doit être interprété comme une preuve d'exécution réussie.

## 6. Contrôles anti-contournement
- Une seule approbation par sujet et par demande ; les doublons sont rejetés.
- Les deux approbations sont liées à authorization_id, version et empreinte.
- Nonce distinct par session d'approbation, avec consommation atomique.
- Refus des clés inconnues, révoquées, expirées ou hors usage.
- Révocation et retrait de rôle recontrôlés au moment de l'exécution.
- Les changements de clé, de rôle ou de politique nécessitent un flux distinct
  de contrôle à deux personnes.
- Les approbateurs ne peuvent pas modifier le contenu après signature.
- Les appels API doivent être idempotents ; toute répétition de demande ou
  callback est détectée et journalisée.
- Le serveur refuse par défaut si le fournisseur d'identité, le registre de
  confiance, le journal d'audit ou le service anti-rejeu est indisponible.

## 7. Journal d'audit
Enregistrer de manière append-only : identifiants de demande/version,
empreinte canonique, sujets approbateurs, identifiants de clés, dates,
résultats de vérification, changements d'état, révocations et motif de blocage.
Ne pas enregistrer de jetons d'identité, secrets, clés privées ou assertions
brutes. L'accès au journal est en lecture seule pour les auditeurs autorisés ;
les corrections sont des événements compensatoires, jamais des réécritures.

## 8. Matrice de tests exigée avant toute intégration
- Deux sujets distincts, deux signatures valides, même empreinte : acceptation
  du dossier d'approbation uniquement.
- Même sujet utilisé deux fois, même personne avec deux sessions : refus.
- Empreintes différentes ou demande modifiée entre A et B : refus.
- Approver A ou B sans rôle actuel, compte désactivé ou assertion expirée : refus.
- Clé inconnue, révoquée, expirée, mauvaise signature ou algorithme substitué : refus.
- Nonce répété, expiré ou consommé concurremment : refus.
- Révocation après la seconde approbation mais avant l'opération : blocage.
- Modification de politique entre A et B : nouvelle approbation exigée.
- Service d'identité, registre, audit ou anti-rejeu indisponible : refus fermé.
- Reviewer identique à operator : refus.
- Tentative de modification de l'environnement ou des limites après approbation : refus.

Les tests doivent inclure des comptes d'essai distincts fournis par un
environnement de test autorisé, et une revue indépendante. Les simulations
locales ne suffisent pas à prouver l'identité ou l'application réelle des rôles.

## 9. Critères de sortie
Ce protocole ne pourra être considéré comme implémenté qu'après :
- choix et configuration approuvés du fournisseur d'identité et du KMS/HSM ;
- registre de rôles et de clés géré hors du client et du dépôt ;
- tests d'intégration avec deux comptes distincts et révocation réelle ;
- preuve de consommation anti-rejeu atomique et audit append-only ;
- revue de sécurité indépendante ;
- vérification des contrôles d'hôte et de runtime séparée du processus
  d'approbation.

Jusqu'à satisfaction de ces critères, aucun passage G2-B à GO n'est permis.

## 10. Garde-fous maintenus
Aucun fournisseur n'est sélectionné, aucun compte n'est créé, aucun secret ou
clé réelle n'est ajouté, aucune modification Supabase n'est appliquée, aucun
investisseur n'est invité, aucun déploiement ou workload n'est exécuté et
aucune dépense n'est engagée par cette spécification.

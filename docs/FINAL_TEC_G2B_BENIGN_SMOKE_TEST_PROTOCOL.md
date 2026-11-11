# FINAL TEC — G2-B protocole de smoke tests locaux inoffensifs

## Statut

Spécification de test uniquement. Cette étape ne lance aucun processus, n'installe
aucun runtime et ne modifie aucune machine.

Dépendances de conception :
- G0 : politique d'autorisation fail-closed ;
- G1 : évaluateur de fixtures synthétiques, CI ciblée réussie ;
- G2-A : validateur statique de profil, CI ciblée réussie sur PR #245.

Les tests G2-B ne sont pas considérés comme exécutés ni réussis par la seule
publication de ce document.

## Objectif limité

Définir une future vérification locale, contrôlée et non hostile, destinée à
confirmer qu'un environnement jetable applique effectivement quelques propriétés
de confinement. Le test ne doit jamais recevoir de code, de commande, de chemin,
d'image ou de paramètre exécutable fourni par un utilisateur.

Le scénario autorisé, s'il est approuvé séparément, est un processus fixe et
déterministe qui :
- démarre dans un environnement temporaire sans privilèges ;
- écrit uniquement un petit fichier de test dans son espace temporaire dédié ;
- lit ce fichier et produit un résultat attendu ;
- termine de lui-même dans un délai très court ;
- ne tente aucune connexion réseau, aucun accès aux secrets et aucune interaction
  avec les ressources de l'hôte.

Ce scénario ne constitue pas un test de pénétration, un benchmark, ni une preuve
de résistance à un attaquant déterminé.

## Conditions préalables obligatoires

Aucun lancement ne peut avoir lieu tant que les conditions suivantes ne sont pas
toutes vérifiées et approuvées :

1. Autorisation écrite spécifique au test G2-B, distincte de l'approbation d'une
   simple PR documentaire.
2. Hôte local ou environnement jetable explicitement choisi ; aucun environnement
   de production ou partagé.
3. Runtime et version identifiés, installés et approuvés par l'opérateur ; aucune
   installation automatique par le test.
4. Image de test minimale, immuable et épinglée par digest ; provenance et digest
   consignés.
5. Profil G2-A validé, puis contrôles effectifs du runtime vérifiés indépendamment.
6. Exécution rootless/non privilégiée, namespaces isolés, racine en lecture seule,
   répertoire temporaire plafonné, aucun montage hôte, socket runtime, secret,
   agent SSH ou périphérique.
7. Réseau désactivé au niveau du runtime ET refusé au niveau de l'hôte ; aucune
   résolution DNS, route sortante ou accès aux métadonnées.
8. Limites réellement appliquées par l'hôte : CPU, mémoire, PID, stockage, volume
   de sortie et durée.
9. Arrêt d'urgence testé avant le scénario nominal ; descendants inclus et aucun
   redémarrage automatique.
10. Journalisation locale minimale, sans données sensibles, avec identifiant de
    run et empreintes des artefacts.

Si une capacité de sécurité n'est pas disponible ou ne peut être vérifiée, le test
est refusé. Aucun mode dégradé n'est accepté.

## Séquence proposée

1. Vérifier l'identité de l'opérateur, l'autorisation, son expiration et son nonce
   à usage unique.
2. Revalider le manifeste avec G0 et le profil déclaré avec G2-A.
3. Vérifier séparément les paramètres réellement actifs du runtime et de l'hôte.
4. Créer un environnement jetable avec limites effectives ; vérifier l'absence
   de réseau et de montages interdits avant le lancement.
5. Lancer uniquement le processus fixe inoffensif décrit ci-dessus.
6. Vérifier le résultat attendu, le code de sortie, la durée et les limites
   observées.
7. Détruire l'environnement et vérifier la disparition de tous les processus
   descendants et des fichiers temporaires.
8. Consigner les résultats et conserver l'état `pending/draft` pour revue humaine.

## Critères d'acceptation

Le scénario nominal n'est acceptable que si :
- le processus fonctionne sous un UID non privilégié ;
- les espaces de noms attendus sont effectivement actifs ;
- la racine est en lecture seule et seul l'espace temporaire autorisé est inscriptible ;
- aucun montage hôte, socket, secret ou périphérique n'est visible ;
- aucune interface ou route réseau utilisable n'est présente ;
- le processus termine dans la durée et les limites définies ;
- le résultat attendu est exact et reproductible ;
- tous les processus et ressources temporaires sont nettoyés.

Un résultat nominal ne prouve pas à lui seul l'efficacité de tous les contrôles.

## Cas d'arrêt immédiat

Refuser ou interrompre si :
- l'autorisation manque, expire ou a déjà été consommée ;
- l'image ou son digest diffère du manifeste ;
- un contrôle effectif ne correspond pas au profil ;
- une interface, route, résolution DNS ou tentative réseau apparaît ;
- un montage hôte, secret, socket ou périphérique inattendu est visible ;
- une limite n'est pas imposée par le système hôte ;
- le délai est dépassé, un processus enfant persiste ou le nettoyage échoue ;
- une erreur de journalisation empêche de reconstituer le run.

Après un arrêt : tuer l'ensemble du groupe de contrôle ou de l'environnement,
révoquer le nonce, interdire le redémarrage et classer le run `aborted` ou
`failed`. Aucun retry automatique.

## Données de preuve minimales

Pour chaque exécution autorisée :
- identifiant du run et référence de l'autorisation ;
- opérateur et horodatages ;
- hôte/runtime/version et digest de l'image ;
- manifeste et version de la politique ;
- résultat des vérifications effectives pré-lancement ;
- limites configurées ET observées ;
- code de sortie, durée, empreinte du petit artefact de test ;
- état de l'arrêt et preuve de nettoyage ;
- identité du réviseur indépendant et décision.

Les empreintes attestent seulement de l'intégrité des octets comparés ; elles ne
prouvent ni l'identité de l'opérateur, ni l'exécution réelle, ni la véracité des
mesures.

## Hors périmètre

G2-B n'autorise pas :
- l'exécution de code utilisateur, de scripts arbitraires ou de charges hostiles ;
- un test réseau, un scan, un test d'évasion ou un test de pénétration ;
- un benchmark matériel ou une mesure de performance ;
- l'accès à un fournisseur, à Internet, à Supabase ou à des secrets ;
- la création d'un environnement cloud ou l'achat de ressources ;
- la publication d'une preuve comme `verified` ou `published`.

Les tests de limites de ressources (G2-C), de refus réseau (G2-D) et d'arrêt/
récupération (G2-E) restent des étapes distinctes avec leurs propres critères et
autorisations.

## Décision de sortie

Ce document prépare une revue de sécurité et une décision d'autorisation séparée.
Il ne vaut pas autorisation d'exécuter G2-B. Tant que le test n'a pas été autorisé,
effectivement exécuté, observé et revu, le statut reste `not_run`, la preuve
`pending` et la publication `draft`.

Aucune fusion, aucun déploiement, aucune modification Supabase, aucun contact
fournisseur, aucun provisionnement et aucune dépense ne sont effectués par cette
spécification.

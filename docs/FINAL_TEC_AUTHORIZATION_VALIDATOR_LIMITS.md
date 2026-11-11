# FINAL TEC — limites du validateur de contrat G0–G2-B

## Objet

Le module `final_tec_authorization_contract.py` vérifie la structure du contrat
cible défini dans la PR #250. Il s'agit d'un validateur de politique local, pas
d'un système d'autorisation de production.

## Contrôles réalisés localement

- schéma versionné strict et refus des champs inconnus ;
- fenêtre temporelle timezone-aware, expiration et révocation déclarée ;
- séparation des identités demandeur/approbateur/opérateur/réviseur ;
- forme de l'approbation, algorithme Ed25519 attendu et signature Base64 de 64 octets ;
- empreintes SHA-256 et comparaison exacte avec l'environnement attendu fourni ;
- réseau interdit, aucun secret et budget nul pour le scénario initial ;
- bornes numériques et présence du contrôleur d'arrêt déclaré ;
- ordre des callbacks : identité, signature, puis consommation du nonce ;
- aucune transition vers exécution et aucune promotion de preuve.

## Frontières de confiance obligatoires

Les callbacks sont des interfaces, pas des garanties fournies par ce module :

1. `signature_verifier` doit vérifier cryptographiquement la signature Ed25519
   contre une clé publique de confiance, avec révocation et rotation. Le module
   ne réalise pas lui-même cette vérification.
2. `identity_verifier` doit interroger une source d'identité et de rôles fiable.
   Le module ne prouve pas l'identité d'un acteur.
3. `nonce_consumer` doit effectuer une consommation durable, atomique et
   transactionnelle. Un dictionnaire ou un verrou en mémoire locale ne garantit
   pas l'anti-rejeu entre processus, machines ou redémarrages.
4. `expected_environment` doit provenir d'une collecte indépendante et fiable.
   Une valeur transmise par le même opérateur que le manifeste n'est pas une
   attestation de l'hôte.
5. La présence déclarée d'un contrôleur d'arrêt ne prouve pas son indépendance,
   son fonctionnement ou le nettoyage effectif des processus.

Le callback de signature reçoit un payload qui inclut les métadonnées
d'approbation (rôle, politique, algorithme et key_id), mais exclut la valeur de
signature elle-même. Le système appelant doit signer et vérifier une
représentation canonique identique. Le format canonique et les bibliothèques
cryptographiques restent à sélectionner et à auditer.

## Tests

Les tests emploient des callbacks simulés et des données fictives. Ils vérifient
le comportement fail-closed et l'ordre des contrôles, pas la cryptographie
réelle, l'identité réelle, le stockage transactionnel, l'OS, les namespaces,
cgroups, le réseau ou l'arrêt système.

## Décision

**LOCAL POLICY VALIDATOR ONLY — NO-GO / NOT_RUN.**

Aucun runtime, processus, workload, hôte, fournisseur, réseau, Supabase, secret,
clé réelle, benchmark ou dépense. Le résultat du module ne doit jamais être
interprété comme `execution_authorized`, `host_controls_verified`,
`verified` ou `published`.

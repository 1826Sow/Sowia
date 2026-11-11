# FINAL TEC — registre anti-rejeu local G0–G2-B

## Objet

Cette implémentation de référence fournit un registre SQLite local à usage
mono-machine. Elle complète l'interface `nonce_consumer(nonce, authorization_id)`
définie dans la PR #251.

## Garanties locales visées

- empreinte SHA-256 du nonce stockée à la place du nonce brut ;
- unicité de l'empreinte par contrainte de clé primaire ;
- consommation via transaction d'écriture SQLite `BEGIN IMMEDIATE` ;
- mise à jour conditionnelle : nonce connu, lié à la bonne autorisation,
  non expiré, non révoqué et non consommé ;
- un seul gagnant en cas de consommations concurrentes sur la même base ;
- persistance après fermeture et réouverture du processus ;
- révocation avant consommation.

## Limites non négociables

Ce composant n'est pas un registre distribué. SQLite local ne prouve pas à lui
seul une cohérence multi-machine, une protection contre un administrateur
malveillant, une sauvegarde inviolable, une haute disponibilité, ni la sécurité
du système de fichiers. Le chemin de base doit être protégé par les permissions
du système d'exploitation et placé sur un stockage local adapté.

Ne pas utiliser ce prototype sur un partage réseau, plusieurs hôtes ou comme
service de production sans étude spécifique, tests de panne, stratégie de
sauvegarde/restauration, contrôle d'accès, surveillance et revue indépendante.

## Intégration avec le validateur

L'adaptateur `SQLiteNonceRegistry.consume_callback` respecte la signature
attendue par la PR #251. L'appelant doit enregistrer préalablement le nonce
après validation de l'émission de l'autorisation. L'ordre d'appel reste :
identité fiable, signature fiable, puis consommation atomique du nonce.

Un échec ou une exception doit bloquer le flux. Le registre ne valide ni la
signature, ni l'identité, ni l'environnement, et n'autorise aucun workload.

## Tests

Les tests couvrent l'enregistrement unique, le rejeu, l'expiration, la
révocation, le mauvais identifiant d'autorisation, la persistance après
réouverture, le stockage du digest, l'adaptateur et 12 tentatives concurrentes
sur une même base locale.

Les tests sont des tests logiciels locaux. Ils ne constituent pas une preuve
de sécurité système, de fonctionnement distribué ou de conformité de production.

## Décision

**LOCAL SQLITE REFERENCE — NO-GO / NOT_RUN FOR G2-B EXECUTION.**

Aucun runtime ou workload lancé, aucune machine hôte inspectée, aucun réseau,
fournisseur, Supabase, secret, clé réelle, benchmark, dépense, merge ou
déploiement. Les preuves restent `pending/draft`.

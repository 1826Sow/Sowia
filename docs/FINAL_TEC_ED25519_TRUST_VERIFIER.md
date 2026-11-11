# FINAL TEC — vérificateur Ed25519 et registre de confiance local

## Statut

Implémentation isolée proposée dans la PR #254. Elle ne constitue ni une
identité humaine authentifiée, ni une preuve d'environnement hôte, ni une
autorisation d'exécution. G2-B demeure **NO-GO / NOT_RUN**.

## Signature

- Algorithme strict : Ed25519 uniquement.
- Bibliothèque cryptographique : `cryptography`.
- Sérialisation signée : JSON Canonicalization Scheme (RFC 8785), via
  `rfc8785`. La signature porte sur le contrat complet sans le champ
  `approval.signature`; le bloc d'approbation restant (rôle, politique,
  algorithme et key_id) est inclus.
- La vérification refuse une clé absente du registre, une signature Base64
  invalide, une mauvaise longueur, une signature incorrecte, un sujet/rôle
  incohérent et une clé hors période de validité.

## Registre de confiance

Le registre est injecté explicitement dans le vérificateur. Il ne peut pas être
fourni par le manifeste à vérifier. Chaque entrée lie key_id, clé publique,
approver_id, rôle et période de validité. La révocation est immédiate. La
rotation est réalisée en ajoutant une nouvelle clé sous un nouvel identifiant ;
l'ancienne peut rester vérificatrice pour les signatures émises avant
`signing_disabled_at`, puis être révoquée si nécessaire.

**Limite importante :** le registre en mémoire est un prototype local. Il doit
être provisionné et protégé par une autorité indépendante avant tout usage réel.
La vérification de clé lie une signature à un identifiant déclaré dans le
registre, mais ne prouve pas à elle seule l'identité réelle d'une personne.
L'`identity_verifier` de production doit provenir d'une source d'identité
autorisée, distincte du dépôt et du manifeste.

## Clés et tests

Les tests créent des paires Ed25519 éphémères à l'exécution. Aucune clé privée
n'est enregistrée dans le dépôt. Les tests couvrent signature valide, altération
du payload, clé inconnue, mauvaise clé, révocation, expiration, rotation,
substitution d'algorithme et discordance approbateur/rôle.

## Hors périmètre

Aucun KMS/HSM, service d'identité réel, secret, Supabase, runtime, conteneur,
workload, réseau externe, dépense, merge ou déploiement. La réussite des tests
ne transforme pas le résultat en autorisation d'exécution.

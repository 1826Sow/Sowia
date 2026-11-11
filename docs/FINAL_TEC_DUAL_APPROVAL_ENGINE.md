# FINAL TEC — moteur de contrôle des approbations doubles

## Statut
Prototype local isolé dans la PR #257. Il vérifie la politique d'approbation
à deux personnes et retourne uniquement
`dual_approval_verified_not_execution_authorized`. Il ne lance aucun processus,
ne vérifie pas l'isolation hôte et ne donne aucun feu vert G2-B. G2-B reste
**NO-GO / NOT_RUN**.

## Fonctionnement
- Le serveur fournit un objet de demande strictement structuré.
- Le moteur calcule SHA-256 sur la représentation JSON canonique RFC 8785.
- Deux approbations exactes sont exigées ; chaque enveloppe lie la demande,
  son empreinte et les métadonnées de l'approbateur.
- Les deux sujets, clés et nonces doivent être distincts.
- Les approbateurs ne peuvent être ni le requester, ni l'operator, ni le reviewer.
- Le rôle, la version de politique, l'algorithme Ed25519 et les fenêtres de
  validité sont contrôlés.
- Les vérifications d'identité et de signature sont déléguées à des interfaces
  injectées qui doivent utiliser des autorités indépendantes.
- Les deux nonces sont transmis ensemble à une interface qui doit les consommer
  dans une transaction atomique unique ; une consommation partielle n'est pas
  conforme au contrat.
- Un événement d'audit append-only doit être confirmé avant que le résultat
  positif de vérification soit retourné.

## Contrats d'intégration
- `signature_verifier(envelope, approval)` vérifie réellement Ed25519 avec un
  registre de confiance externe au manifeste.
- `identity_verifier(subject, role, context)` vérifie le sujet authentifié,
  son statut et son rôle courant auprès d'une source autoritative.
- `nonce_pair_consumer(authorization_id, nonce_records)` consomme les deux
  nonces atomiquement, ou aucun.
- `audit_append(event)` écrit un événement immuable et retourne uniquement
  après confirmation durable.

Les callbacks de test sont des substituts de test, pas des mécanismes de
confiance utilisables en production. Le module n'est pas encore raccordé à
l'Ed25519 verifier, à un fournisseur OIDC, à un stockage anti-rejeu distribué
ou à un journal d'audit réel.

## Limite importante : échec après consommation des nonces
Si l'audit append-only échoue après la consommation atomique des deux nonces,
la demande est bloquée et les nonces restent consommés. Il faut créer une
nouvelle demande/version et de nouveaux nonces ; aucune tentative de réutiliser
les mêmes preuves n'est permise. Cette stratégie privilégie le refus fermé à
la réutilisation potentielle d'une autorisation.

## Tests locaux automatisés
La suite couvre l'approbation à deux sujets, la réutilisation d'un sujet ou
d'une clé, l'altération du payload, l'identité invalide, l'échec de consommation
des nonces, l'expiration, la séparation des rôles et l'échec d'audit. Les
callbacks simulés ne prouvent ni l'identité réelle ni le fonctionnement d'un
service externe.

## Hors périmètre
Aucun compte, fournisseur OIDC, KMS/HSM, secret, service d'audit, Supabase,
migration, déploiement, accès investisseur ou workload n'est configuré.
Aucune dépense n'est engagée.

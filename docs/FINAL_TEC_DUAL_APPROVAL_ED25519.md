# FINAL TEC — raccordement Ed25519 des approbations doubles

## Ce qui est ajouté
Le module `final_tec_dual_approval_ed25519.py` fournit un adaptateur
cryptographique compatible avec le callback `signature_verifier` du moteur
`final_tec_dual_approval.py`.

Pour chaque approbation, il :
- recherche la clé par `key_id` dans un registre public injecté, indépendant
  du contenu soumis ;
- lie `subject_id` et `role` aux attributs du registre de confiance ;
- vérifie l'algorithme Ed25519, la fenêtre de validité, la révocation et la
  désactivation de signature ;
- vérifie la signature sur l'enveloppe canonique RFC 8785 qui comprend la
  demande complète, son digest et les métadonnées d'approbation.

Les tests créent deux paires de clés Ed25519 éphémères et signent réellement
les deux enveloppes. Aucune clé privée n'est enregistrée dans le dépôt.

## Ce que cela prouve
Les tests démontrent que le code vérifie des signatures Ed25519 authentiques
produites avec les clés privées temporaires correspondantes, et rejette une
demande modifiée, une clé inconnue, une clé publique incorrecte, une clé
révoquée, un encodage invalide et une discordance sujet/clé.

## Ce que cela ne prouve pas
- Le callback d'identité dans les tests est simulé. Aucun fournisseur OIDC,
  compte réel, MFA ou annuaire de rôles n'est connecté.
- Le registre de clés reste un objet fourni au processus ; aucun service
  d'administration ou de provisionnement externe n'est configuré.
- Le callback anti-rejeu et le journal d'audit sont des substituts de test.
  La consommation atomique réelle de deux nonces et l'audit durable restent
  à raccorder.
- Ce raccordement n'atteste pas l'hôte, le runtime, l'isolation ou le workload.
- Il ne délivre aucune autorisation d'exécution et ne lance aucun processus.

## Statut
Prototype cryptographique isolé, PR en brouillon. Aucun secret, clé privée
réelle, KMS/HSM, OIDC, Supabase, déploiement ou workload. G2-B reste
**NO-GO / NOT_RUN**.

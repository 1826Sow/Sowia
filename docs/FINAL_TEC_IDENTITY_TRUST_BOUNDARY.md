# FINAL TEC — frontière de confiance identité et approbations

## Statut
Spécification préparatoire liée à la PR #254. Aucun fournisseur d'identité,
compte, clé réelle, secret ou endpoint n'est configuré. Aucun utilisateur réel
n'est authentifié par ce document. G2-B reste NO-GO / NOT_RUN.

## Objectif de sécurité
Éviter qu'un identifiant `approver_id` écrit dans un manifeste ou qu'une clé
publique auto-déclarée suffise à créer une approbation de confiance. La preuve
doit provenir d'une chaîne indépendante du dépôt et du manifeste.

## Chaîne de confiance cible
1. Un fournisseur d'identité externe authentifie l'approbateur (OIDC ou mécanisme
   équivalent) et délivre une assertion vérifiable.
2. Un service d'autorisation côté serveur vérifie l'émetteur, l'audience,
   l'expiration, le nonce de session, l'identifiant stable du sujet et les
   facteurs d'authentification requis.
3. Une politique indépendante attribue le rôle `security-approver` au sujet.
   Le rôle ne doit jamais être accepté depuis le manifeste client.
4. Le service de clés de confiance administre les clés publiques Ed25519,
   leurs identifiants, périodes de validité, statut, révocation et rotation.
   Toute modification du registre est authentifiée, auditée et soumise à
   séparation des rôles.
5. Le service d'approbation construit le payload canonique RFC 8785 à partir
   des données validées côté serveur, puis signe avec une clé privée conservée
   dans un KMS/HSM ou service équivalent. La clé privée n'est jamais livrée au
   navigateur, à l'application cliente, au dépôt ou au manifeste.
6. Le validateur FINAL TEC vérifie la signature, la clé publique approuvée,
   l'identité et le rôle issus de sources distinctes, puis consomme atomiquement
   le nonce. Une approbation valide ne prouve pas l'isolation de l'hôte.

## Contrat d'interface minimal
- `identity_verifier(subject_id, role, assertion_context)` doit échouer fermé
  si l'assertion est absente, expirée, mal signée, mauvais issuer/audience,
  sujet désactivé ou rôle non attribué.
- `trust_registry.get(key_id)` ne renvoie que des clés publiées par une
  autorité de confiance indépendante ; le manifeste ne peut ni ajouter ni
  remplacer une clé.
- `approval_signer.sign(canonical_payload)` est une opération côté serveur,
  authentifiée et autorisée, protégée par KMS/HSM ; chaque signature est liée
  à l'identité, au rôle, à la politique, à l'environnement, aux limites et à
  l'identifiant d'autorisation.
- Les opérations d'ajout, rotation, suspension et révocation de clés sont
  journalisées dans un audit append-only, avec approbation à deux personnes
  pour les changements sensibles.
- Les identifiants de session et assertions d'identité ne sont pas conservés
  dans les journaux en clair ; seuls les identifiants nécessaires, empreintes
  et résultats minimisés sont conservés.

## Contrôles obligatoires avant toute intégration réelle
- Vérification cryptographique des assertions OIDC selon les métadonnées
  officielles de l'émetteur, algorithmes explicitement autorisés et rotation
  des clés JWKS ; refus de `none`, des émetteurs/audiences inattendus et des
  clés inconnues.
- Vérification du statut du compte et de l'affectation du rôle à chaque
  approbation, pas seulement lors de la connexion initiale.
- Authentification multifacteur résistante au phishing pour les approbateurs
  privilégiés, selon les capacités du fournisseur retenu.
- Protection KMS/HSM, séparation des environnements, rotation planifiée,
  révocation d'urgence testée et sauvegarde contrôlée du registre.
- Séparation requester / approver / operator / reviewer, vérifiée côté serveur.
- Tests négatifs : assertion falsifiée, mauvais issuer/audience, token expiré,
  sujet désactivé, rôle retiré, clé inconnue/révoquée, substitution
  d'algorithme, rejeu et tentative d'auto-approbation.
- Revue indépendante de sécurité et tests d'intégration avec deux comptes
  réellement distincts avant toute décision de mise en service.

## Décisions non prises
Aucun fournisseur OIDC, KMS/HSM, politique MFA, hébergement, région, durée de
rétention ou modèle de gouvernance n'est choisi ici. Le choix devra tenir compte
des coûts, de la juridiction, de la disponibilité et de la possibilité d'un
fonctionnement sans dépendance excessive à un fournisseur.

## Interdictions maintenues
Aucun compte utilisateur réel, clé réelle, secret, connexion Supabase, migration,
exposition investisseurs, déploiement, dépense ou workload n'est autorisé par
cette spécification. Elle ne fait pas passer G2-B à GO.

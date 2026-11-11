# FINAL TEC — adaptateur d'identité OIDC fail-closed

## Ajout
`final_tec_oidc_identity.py` fournit un vérificateur d'identité compatible
avec le callback `identity_verifier(subject_id, role, context)` du moteur
double approbation.

Il vérifie :
- signature d'un ID token OIDC RS256 avec une clé résolue par `kid` depuis
  une source JWKS de confiance injectée ;
- issuer et audience strictement configurés ;
- claims obligatoires `iss`, `aud`, `sub`, `iat`, `exp`, `nonce`,
  `auth_time`, `acr` et `amr` ;
- correspondance du sujet avec l'approbateur attendu ;
- nonce de session comparé en temps constant ;
- fraîcheur de l'authentification ;
- niveau `acr` et méthode `amr` exigés par la politique ;
- affectation actuelle du rôle via un résolveur indépendant interrogé à
  chaque approbation.

Algorithme accepté dans ce prototype : RS256 uniquement. L'algorithme n'est
jamais choisi à partir d'une valeur non fiable du manifeste. Les erreurs de
résolution de session, de clé ou de rôle entraînent un refus.

## Frontières d'injection obligatoires
- `signing_key_resolver(kid)` doit consulter le JWKS officiel de l'émetteur
  via HTTPS et vérifier l'origine, le cache et la rotation des clés.
- `assertion_resolver(context)` doit retrouver la session d'approbation
  côté serveur et retourner son ID token et le nonce OIDC attendu. Il ne doit
  jamais accepter un token ou nonce depuis le manifeste client. La session
  doit être liée à l'approbation et protégée contre le rejeu.
- `role_resolver(subject, role)` doit interroger la source d'autorité actuelle
  et refuser les comptes désactivés ou rôles retirés.

Les valeurs ACR/AMR sont spécifiques au fournisseur. La politique de
production doit choisir des valeurs documentées par le fournisseur et
démontrer qu'elles correspondent à une authentification résistante au
phishing. La chaîne de test utilise des valeurs fictives : elle ne prouve pas
la qualité MFA d'un fournisseur réel.

## Tests
Les tests créent des clés RSA éphémères et signent des ID tokens de test. Ils
couvrent issuer, audience, expiration, sujet, nonce, fraîcheur auth_time,
ACR/AMR, kid inconnu, rôle retiré, panne du résolveur et algorithme `none`.
Un test d'intégration passe par le callback réel du moteur double approbation.

## Limites
- Aucun fournisseur OIDC n'est choisi ou connecté.
- Aucun JWKS réel n'est téléchargé ; aucun compte ni session utilisateur réel
  n'est authentifié.
- Le stockage des sessions et la consommation du nonce OIDC restent des
  adaptateurs serveur à fournir et à tester contre le rejeu.
- Le résolveur de rôle reste une interface injectée ; aucun annuaire ou
  service de gouvernance réel n'est raccordé.
- Ce composant ne gère pas l'administration ou le provisionnement des clés
  Ed25519 d'approbation. Il authentifie un sujet OIDC ; la confiance de
  signature Ed25519 reste distincte.
- Aucun KMS/HSM, déploiement, workload ou autorisation d'exécution.

## Statut
Prototype OIDC hors ligne, PR en brouillon dépendante de #260. Les tests CI
doivent être confirmés sur le commit final. G2-B reste **NO-GO / NOT_RUN**.

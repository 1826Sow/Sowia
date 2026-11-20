# Configuration de l'authentification Supabase native Android

L'application Android utilise l'URL du projet Supabase et sa clé publique anon/publishable, injectées au moment de la compilation. Elle ne doit jamais embarquer la clé `service_role`, une clé secrète Supabase, une clé fournisseur IA ou un secret PayPal.

## Configuration locale

Dans `android/local.properties` (fichier ignoré par Git), définir :

```properties
SOWIA_SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
SOWIA_SUPABASE_PUBLISHABLE_KEY=YOUR_PUBLIC_PUBLISHABLE_KEY
# Ancienne clé anon acceptée si nécessaire :
# SOWIA_SUPABASE_ANON_KEY=YOUR_PUBLIC_ANON_KEY
```

Les mêmes variables peuvent être fournies à Gradle ou à la CI. La clé publique publishable est préférée ; une ancienne clé anon est également acceptée. Ne jamais utiliser une clé `service_role` ou une clé secrète.

La CI peut compiler avec une configuration Supabase vide pour les contrôles de construction. Dans ce cas, l'authentification et les appels aux services restent indisponibles.

## Fonctionnement de la session

- Connexion e-mail/mot de passe via Supabase Auth.
- Conservation locale des jetons dans les préférences privées, chiffrés avec AES-GCM ; la clé de chiffrement est conservée dans Android Keystore.
- Conservation de `expires_at` dans la session chiffrée.
- Avant les appels authentifiés pris en charge (santé, conversations, projets, historique, Assistant et PDF), l'application vérifie l'expiration et renouvelle le jeton lorsqu'il approche de sa limite.
- Un verrou partagé sérialise les renouvellements dans le processus Android afin d'éviter plusieurs rotations concurrentes du refresh token.
- Les anciennes sessions qui ne contiennent pas encore `expires_at` sont renouvelées au prochain appel authentifié.
- La déconnexion retire la session locale et tente de terminer la session Supabase.

Un renouvellement réussi dans le code ne remplace pas un test sur appareil réel, notamment après une longue période d'inactivité, une perte réseau ou une révocation de session.

## Services et sécurité

- L'Assistant mobile passe par la fonction Edge Supabase `mobile-chat`. Les clés Groq/OpenAI et la sélection du fournisseur restent côté serveur.
- Les données privées doivent rester protégées par les politiques RLS et les contrôles d'identité côté serveur. L'identifiant utilisateur ne doit jamais être considéré comme fiable s'il vient uniquement du client.
- Les tests d'isolation entre deux comptes doivent être exécutés uniquement sur le projet Supabase de test dédié `SOWIA - TEST`, jamais sur la production. Voir [tests/integration/README.md](../tests/integration/README.md).

## Limites connues

La connexion e-mail/mot de passe et le renouvellement de session sont implémentés. La création de compte native, la récupération de mot de passe et les parcours OAuth/PKCE ne sont pas déclarés comme pris en charge par cette configuration. Les essais de bout en bout sur appareil réel restent obligatoires avant publication.

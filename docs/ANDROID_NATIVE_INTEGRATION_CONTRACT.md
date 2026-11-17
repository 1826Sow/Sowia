# SOW IA — contrat d'intégration Android natif

## Décision d'architecture

L'application Android native est un client supplémentaire de SOW IA. Elle ne remplace pas Streamlit et ne doit pas réimplémenter les règles métier sensibles dans le téléphone.

- **Identité et session :** Supabase Auth avec Authorization Code + PKCE. Le client Android utilise uniquement la clé publique anon/publishable et le jeton de l'utilisateur.
- **Données utilisateur :** accès à Supabase Database et Storage avec le JWT utilisateur et les politiques RLS existantes.
- **Fonctions IA et actions privilégiées :** appels HTTPS vers des fonctions serveur dédiées (Supabase Edge Functions ou API backend contrôlée). Le serveur valide le JWT, vérifie l'utilisateur et les droits Premium avant toute action.
- **Secrets :** aucune clé service_role, clé fournisseur IA, PayPal secret ou secret webhook dans l'APK/AAB, les ressources Android ou le dépôt.
- **Web :** l'application Streamlit existante reste intacte et continue d'être la référence fonctionnelle pendant la transition.

## Contrats de service à stabiliser avant le client Android

Les chemins ci-dessous sont des contrats proposés, pas des endpoints actuellement déployés. Ils ne doivent être appelés par l'application qu'après implémentation et tests côté serveur.

| Fonction | Contrat proposé | Règles |
|---|---|---|
| Santé API | `GET /functions/v1/mobile-health` | Réponse minimale, sans secret ni donnée personnelle |
| Assistant | `POST /functions/v1/mobile-chat` | JWT requis, limites de débit, validation du contenu, droits et quota vérifiés côté serveur |
| Conversations | Supabase REST sur `sowia_messages` ou fonction dédiée | Filtrage par utilisateur, session et espace ; RLS obligatoire |
| Projets | Supabase REST sur le registre existant ou fonction dédiée | Réutiliser le schéma et les statuts déjà utilisés par le web |
| PDF | Supabase Storage privé + fonction d'analyse | Vérifier propriétaire, taille, type MIME, quota et droits ; URL signée courte si nécessaire |
| Mémoire | Tables existantes via JWT/RLS ou fonction dédiée | Ne jamais utiliser service_role côté mobile |

### Format minimal de réponse de l'assistant

Requête JSON proposée :
```json
{
  "message": "Question de l'utilisateur",
  "workspace_id": "personal",
  "conversation_id": "identifiant-de-session"
}
```

Réponse JSON proposée :
```json
{
  "conversation_id": "identifiant-de-session",
  "answer": "Réponse de SOW IA",
  "created_at": "2026-01-01T12:00:00Z"
}
```

Le serveur doit dériver l'identité depuis le JWT validé ; il ne doit jamais accepter un `user_id` fourni par le client comme preuve d'identité. Les valeurs ci-dessus illustrent le contrat et ne sont pas des identifiants réels.

## Parcours Android

1. Connexion / inscription via Supabase Auth PKCE et navigateur système, avec URI de redirection vérifiée et App Links/intent filter correctement configurés.
2. Conservation des jetons via le mécanisme sécurisé du SDK et du système Android ; renouvellement, expiration et déconnexion testés.
3. Chargement du profil et des espaces autorisés après authentification.
4. Assistant : historique paginé, envoi, état de chargement, erreurs réseau et reprise sans doublons.
5. « Mes échanges & projets » : réutilisation du registre existant, statuts En cours / À tester / Validé / Terminé et reprise de la conversation associée.
6. Laboratoire PDF : sélection locale, validation avant envoi, progression, erreurs, téléchargement et suppression selon les règles de stockage existantes.
7. Compte : paramètres, état de session, déconnexion et procédure de suppression de compte.

## Sécurité et conformité obligatoires

- RLS activée et vérifiée pour chaque table exposée ; aucune politique permissive temporaire.
- Vérification serveur du JWT et de `auth.uid()` ; ne pas faire confiance à un identifiant utilisateur envoyé dans le corps HTTP.
- Contrôle des droits Premium exclusivement côté serveur.
- HTTPS uniquement ; ne pas activer le trafic HTTP en clair.
- Pas de journalisation des jetons, clés, contenus privés de PDF ou conversations complètes.
- Limites de taille, type de fichier, débit, durée et coût sur les fonctions IA.
- Déconnexion qui efface les jetons locaux et révoque la session lorsque le fournisseur le permet.
- Politique de confidentialité, suppression du compte et informations Google Play alignées sur les traitements réels.

## Séquence de réalisation

### A — Socle Android
- Dépendance Supabase Kotlin SDK et configuration par BuildConfig/variables non secrètes.
- INTERNET permission (déjà déclarée dans le manifeste).
- Client HTTP avec timeouts, gestion des erreurs et TLS standard.
- Navigation Compose conservant le bouton Retour visible et la pile de navigation.

### B — Authentification
- PKCE natif, redirection vérifiée, persistance sécurisée, rafraîchissement et logout.
- Tests de session expirée, annulation OAuth, réseau hors ligne et reprise après fermeture.

### C — Services métier
- Contrat serveur mobile-chat implémenté et testé avant de connecter l'interface Assistant.
- Conversations et projets reliés aux tables réelles avec RLS.
- PDF relié au bucket privé et à une fonction d'analyse autorisée.

### D — Distribution
- Tests unitaires, tests instrumentés et tests sur appareils physiques.
- AAB signé avec secrets GitHub Actions protégés (keystore et mots de passe), jamais stockés dans Git.
- Piste interne Google Play, vérification des formulaires de confidentialité, suppression de compte et métadonnées.
- Publication publique uniquement après validation Google.

## État vérifiable à la création de ce document

- L'application Android est encore un prototype Compose statique.
- Le manifeste déclare maintenant la permission INTERNET.
- Le dépôt web contient les helpers Supabase côté Streamlit, mais cela ne constitue pas un SDK Android ni une API mobile.
- Les endpoints de ce document sont des contrats de conception : aucun n'est déclaré déployé.
- La compilation AAB non signée est automatisée, mais un build réussi et un AAB signé doivent être confirmés séparément.

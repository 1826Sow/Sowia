# SOW IA — application Android native

Cette application Android native (Kotlin + Jetpack Compose) est le client mobile du projet SOW IA. Elle conserve l'application web Streamlit existante : les deux interfaces sont distinctes et partagent les services Supabase prévus par le projet.

## État fonctionnel du code

Les fonctionnalités suivantes sont présentes dans le code Android :

- Interface d'accueil SOW IA, navigation entre les espaces Personnel et Professionnel, retour dans l'application et gestion du bouton « VALIDER ».
- Connexion Supabase par e-mail et mot de passe ; session conservée de manière chiffrée avec AES-GCM et une clé protégée par Android Keystore.
- Validation et renouvellement du jeton de session avant les appels authentifiés, avec sérialisation des renouvellements pour limiter les conflits de rotation du refresh token.
- Accès à l'Assistant via la fonction Edge Supabase `mobile-chat`. Les clés des fournisseurs d'IA restent côté serveur.
- Chargement des conversations, de l'historique et des projets via les API Supabase.
- Laboratoire PDF : sélection, dépôt dans le stockage privé, extraction de texte et OCR, analyse via l'Assistant et suppression du document.

La présence de ces fonctions dans le dépôt et la réussite d'une compilation ne prouvent pas à elles seules leur fonctionnement sur tous les appareils ou comptes.

## Éléments encore à valider ou à compléter

- Essais de bout en bout sur un appareil Android réel : connexion, expiration/renouvellement, déconnexion, Assistant, historique, projets et cycle complet d'un PDF.
- Tests RLS multi-comptes dans le projet Supabase de test dédié. Ils sont suspendus tant que les identifiants et la confirmation du projet de test ne sont pas configurés ; la production ne doit jamais être utilisée.
- Signature de production avec le certificat d'importation Android déjà enregistré pour l'application. Ne pas créer de nouvelle clé pour contourner un problème de mot de passe.
- Publication Google Play, qui dépend également de la récupération de l'accès à la Play Console et de la résolution du problème de signature.
- Certaines rubriques de l'interface peuvent encore afficher un état « en préparation » ; leur présence visuelle ne signifie pas qu'un service complet est déjà disponible.

## Configuration Android

- JDK 17
- Android SDK correspondant au `compileSdk` du projet
- Gradle Wrapper du dépôt

Pour connecter un environnement Supabase, suivre [SUPABASE_AUTH_SETUP.md](SUPABASE_AUTH_SETUP.md). Seules l'URL du projet et la clé publique anon/publishable sont autorisées dans la configuration du client Android. Ne jamais intégrer une clé `service_role`, un secret Supabase, une clé Groq/OpenAI ou un secret PayPal dans l'application.

## Compilation locale

Depuis le dossier `android/` :

```bash
./gradlew :app:assembleDebug
```

L'APK debug sert aux essais. Elle n'est pas signée avec le certificat d'importation Play et ne doit pas être présentée comme une version publiable ni utilisée pour remplacer une installation Play Store existante.

## Règle de livraison

Toute modification doit préserver l'architecture et les fonctionnalités existantes. Une compilation réussie est un contrôle de construction, pas une validation fonctionnelle. Avant toute publication, vérifier le certificat attendu, les tests automatisés, les contrôles de sécurité et les scénarios sur appareil réel.

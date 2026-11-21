# SOW IA — application Android

Le dépôt contient un client Android natif Kotlin/Gradle qui ouvre le tableau de bord SOW IA hébergé dans un WebView sécurisé. Il s'agit d'une enveloppe Android connectée au service web existant, et non encore d'une application entièrement native.

## Fonctionnalités présentes dans le code

- Identifiant Android principal : `com.sowkeys.sowia` ; variante parallèle distincte pour les tests.
- Écran de lancement Android et activité de tableau de bord.
- Chargement HTTPS du tableau de bord Streamlit existant.
- JavaScript et stockage DOM activés pour la compatibilité Streamlit ; contenu mixte HTTP bloqué et accès arbitraire aux fichiers locaux désactivé.
- Sélecteur de documents Android relié au mécanisme de chargement de fichiers du WebView, pour permettre la sélection d'un PDF.
- Gestion du bouton Retour Android, avec priorité à la navigation interne SOW IA puis à l'historique WebView.
- Module Kotlin de laboratoire PDF et client Supabase présents dans le dépôt ; leur intégration complète dans le parcours de lancement et leurs tests sur appareil restent à vérifier.

## Limites à ne pas masquer

- L'assistant, l'historique, les espaces personnel/professionnel et les outils métier restent servis par l'application web ; ils ne sont pas encore tous réimplémentés en écrans natifs.
- Le contrat d'intégration native Supabase PKCE et les endpoints mobiles décrits dans la documentation sont des exigences de conception, pas la preuve que tous ces services sont déployés.
- Une compilation réussie ne prouve pas le bon fonctionnement sur appareil : authentification, session, import PDF, navigation Retour, reprise réseau et téléchargement doivent être testés sur un téléphone réel.
- Aucun APK/AAB n'est considéré comme livrable Google Play tant que la compilation, la signature avec le certificat d'envoi déjà enregistré et les contrôles de distribution ne sont pas vérifiés.

## Sécurité

- Ne jamais intégrer de clé Supabase `service_role`, de clé fournisseur IA, de secret PayPal ou de secret webhook dans l'application.
- La configuration mobile embarquée se limite à l'URL Supabase HTTPS et à la clé publique anon/publishable ; les autorisations de données reposent sur l'identité utilisateur et RLS.
- Ne jamais générer, remplacer ou modifier le certificat de signature permanent sans décision explicite du propriétaire.

## Compilation et vérification

Le projet Android se trouve dans ce dossier. Il utilise Gradle, Kotlin, Jetpack Compose et JDK 17. Les workflows GitHub Actions du dépôt proposent des builds de test et des builds de distribution. Un APK de débogage est réservé aux essais ; la publication Google Play nécessite un AAB signé avec le certificat d'envoi déjà enregistré, puis les vérifications et validations Play Console.

## Documentation de référence

- [Contrat d'intégration Android natif](../docs/ANDROID_NATIVE_INTEGRATION_CONTRACT.md)
- [Feuille de route de distribution mobile et internationale](../docs/DISTRIBUTION_MOBILE_ET_INTERNATIONALE.md)

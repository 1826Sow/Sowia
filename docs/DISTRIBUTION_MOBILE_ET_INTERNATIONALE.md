# SOW IA — feuille de route de distribution mobile et internationale

## Décision produit

SOW IA doit rester un produit unique avec un socle applicatif et des comptes communs. La version web Streamlit existante est conservée : la distribution mobile ne doit pas provoquer une réécriture prématurée ni une perte des fonctions, données, historiques ou droits d'accès.

Cibles de distribution :
- Web : application HTTPS accessible dans le monde entier.
- Android : application installable et publiable sur Google Play après validation technique et conformité.
- iOS/iPadOS : application distribuable via l'App Store après adaptation et validation Apple.
- Ordinateur : accès web responsive ; une application de bureau dédiée n'est pas un prérequis à la première sortie.

## Architecture recommandée par étapes

### Étape 1 — Stabiliser le produit web (prérequis)

- Conserver Streamlit comme interface web et Supabase comme socle d'identité, de données et de stockage.
- Finaliser et tester la navigation mobile, le bouton Retour, la déconnexion, l'authentification et la récupération de session.
- Vérifier les parcours PDF, mémoire, historique, projets, téléversement et téléchargement sur Android, iOS et ordinateur.
- Vérifier HTTPS, URL de redirection OAuth, politiques RLS, stockage privé, gestion des erreurs et limites d'API.
- Ne jamais embarquer de clés secrètes ou de clés de service dans une application mobile ou dans le navigateur.
- Définir une politique de confidentialité, des conditions d'utilisation, un contact d'assistance et une procédure de suppression de compte/données.

**Critère de sortie :** aucun défaut bloquant de sécurité ou de parcours utilisateur ; tests automatisés et tests manuels multi-appareils consignés.

### Étape 2 — Préparer une expérience installable (PWA si compatible)

- Étudier la compatibilité réelle de Streamlit avec une Progressive Web App : manifeste, icônes, installation, comportement plein écran, liens profonds, mises à jour et authentification.
- Ne pas déclarer l'application « PWA » tant que ces points ne sont pas vérifiés sur des appareils réels.
- Si les limites de Streamlit empêchent une expérience PWA fiable, conserver le site responsive et construire une couche mobile dédiée qui réutilise les mêmes services sécurisés.

**Critère de sortie :** installation, ouverture, connexion, navigation et mise à jour validées sur Android et iOS.

### Étape 3 — Android / Google Play

- Choisir la solution après le test PWA : Trusted Web Activity si le site répond aux exigences web et de validation ; sinon application Android dédiée (par exemple une couche native ou multiplateforme) connectée aux mêmes services SOW IA.
- Préparer identifiant d'application, signature, versionnement, icône, captures d'écran, description, classification du contenu et fiche de confidentialité.
- Tester sur plusieurs tailles d'écran et versions Android, y compris les flux OAuth, fichiers, liens externes, retours système et déconnexion.
- Produire un Android App Bundle signé et le tester sur une piste interne/fermée avant toute publication publique.
- Respecter les règles Google Play applicables au moment du dépôt, notamment celles concernant les comptes, la confidentialité, les données et les fonctionnalités.

**Critère de sortie :** validation des tests, dossier de publication complet et approbation de Google Play.

### Étape 4 — iPhone / iPad / App Store

- Évaluer une application iOS dédiée ou une enveloppe native seulement si elle apporte une expérience mobile utile et conforme aux règles Apple.
- Tester connexion, déconnexion, liens profonds, fichiers, navigation, accessibilité, performances et reprise de session.
- Préparer les métadonnées, captures, informations de confidentialité, politique de suppression de compte et compte de démonstration si demandé.
- Soumettre via le processus Apple et corriger les éventuels retours de revue.

**Critère de sortie :** application validée par Apple et disponible dans les régions choisies.

### Étape 5 — Déploiement international

- Définir les pays/régions de lancement selon la disponibilité des services, les langues, les obligations légales et les moyens de support.
- Préparer les traductions professionnelles de l'interface, des fiches stores, de l'aide et des documents légaux.
- Vérifier les règles de protection des données, transferts internationaux, conservation/suppression, taxes et paiements selon les marchés.
- Déployer progressivement, suivre les erreurs et retours, puis élargir les pays.

## Ordre de priorité

1. Fiabilité et sécurité de l'application web actuelle.
2. Expérience mobile responsive et parcours de compte.
3. Étude et validation PWA.
4. Distribution Android.
5. Distribution iOS.
6. Extension pays/langues et éventuelle application ordinateur.

## Points de contrôle actuels

- Le dépôt décrit actuellement SOW IA comme une application web Streamlit.
- La présence d'une URL web ne signifie pas qu'un paquet Android ou iOS existe.
- Aucun APK/AAB, archive iOS, fiche Play Store ou fiche App Store n'est déclaré prêt par ce document.
- Les publications restent conditionnées aux tests réels, à la configuration des comptes développeur et à l'approbation des plateformes.
- Les coûts éventuels des comptes développeur, services d'hébergement, API et conformité devront être vérifiés avant engagement ; aucune dépense ne doit être engagée sans validation du propriétaire.

## Règle de préservation

Toute évolution mobile doit réutiliser autant que possible l'authentification Supabase, les données et les services existants. Ne pas supprimer, remplacer ou réinitialiser les fonctions de l'application web pour fabriquer une version mobile. Chaque changement doit être isolé, testé et documenté avant fusion dans `main`.

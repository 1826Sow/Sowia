# SOW IA — dossier de conception du prototype Android

**Statut :** spécification technique préparatoire. Ce document ne prétend pas qu'une application Android a déjà été développée, compilée ou publiée.

## 1. Décision d'architecture

Conserver l'application Streamlit actuelle comme produit web de référence. Le prototype Android doit être un client mobile distinct qui consomme des interfaces serveur sécurisées et partage l'identité et les données SOW IA via Supabase.

Ne pas intégrer l'interface Streamlit dans une WebView comme solution finale par défaut : cette approche peut reproduire les limites de navigation, de clavier, de fichiers et d'authentification du site mobile. Une TWA n'est envisageable que si le site devient une PWA réellement compatible et si les parcours requis sont validés sur appareils réels.

**Cible technique à évaluer pour le prototype :** client Android natif Kotlin avec Jetpack Compose, architecture par couches (UI, domaine, données), appels HTTPS vers des API serveur contrôlées. Une solution multiplateforme pourra être comparée avant le premier sprint, mais ne doit pas retarder la stabilisation du web.

## 2. Ce que le dépôt confirme aujourd'hui

- L'application web est construite avec Streamlit et son point d'entrée est `app.py`.
- La configuration est centralisée dans `settings.py` et `config.py`.
- L'authentification web s'appuie sur Supabase Auth avec un flux GitHub OAuth/PKCE.
- Le code web utilise des composants Streamlit et un stockage navigateur pour un identifiant aléatoire de portée OAuth ; ce mécanisme n'est pas automatiquement réutilisable dans une application native.
- Les données et fichiers reposent sur des modules Supabase et des politiques RLS ; le client mobile devra être authentifié comme utilisateur et ne devra jamais recevoir de clé `service_role`.
- Les fonctions PDF, mémoire, historique, projets et paiements sont réparties dans des modules Python existants. Elles ne deviennent pas des API mobiles simplement parce qu'elles existent dans le dépôt.

## 3. Architecture cible

```text
Application Android (Kotlin / Compose)
  ├── Présentation : écrans, navigation, états, accessibilité
  ├── Domaine : cas d'usage et règles d'affichage
  ├── Données : clients HTTPS, dépôt local temporaire, cache
  └── Authentification : Supabase Auth natif / OAuth PKCE
             │
             │ HTTPS + jeton utilisateur à durée limitée
             ▼
Services serveur SOW IA (à définir et sécuriser)
  ├── Authentification et autorisation
  ├── Conversations / mémoire / projets
  ├── Documents PDF et stockage privé
  ├── Fonctions IA et recherche web
  └── Droits Premium / paiements (contrôle serveur)
             │
             ▼
Supabase : Auth, Postgres avec RLS, Storage privé

Application Streamlit existante ─── mêmes services et données autorisés
```

Le schéma est une cible, pas une description d'une API déjà disponible. Avant d'exposer une fonction Python, définir un contrat d'API versionné, valider l'identité côté serveur, vérifier les droits sur chaque ressource et journaliser les erreurs sans enregistrer de secrets.

## 4. Authentification et sécurité

1. Utiliser le flux OAuth natif avec PKCE et navigateur système ; ne pas copier le composant de stockage local Streamlit dans Android.
2. Enregistrer les URI de redirection Android autorisées dans le fournisseur d'identité, avec validation des domaines et empreintes de signature lorsque nécessaire.
3. Stocker les jetons selon les recommandations Android, protéger les données sensibles au repos et effacer la session locale à la déconnexion.
4. Transmettre uniquement le jeton utilisateur requis aux API HTTPS ; vérifier signature, expiration, audience et utilisateur côté serveur.
5. Appliquer l'autorisation au niveau de chaque opération et de chaque objet. Les politiques RLS restent une défense complémentaire, pas un remplacement des contrôles serveur.
6. Ne jamais intégrer dans l'APK/AAB : clé Supabase `service_role`, clé API du fournisseur IA, secret PayPal, secret OAuth ou autre secret serveur.
7. Prévoir révocation/expiration de session, erreurs réseau, renouvellement sécurisé et déconnexion explicite.
8. Les paiements restent hors du premier prototype. Toute intégration ultérieure devra appliquer les règles des stores et le contrôle d'abonnement côté serveur.

## 5. Écrans du prototype — périmètre initial

| Écran | Fonction minimale | Critère d'acceptation |
|---|---|---|
| Accueil / connexion | Présenter SOW IA et ouvrir la connexion | Aucun accès aux données privées sans session valide |
| Tableau de bord | Accès aux fonctions activées | Chargement lisible, états vide/erreur |
| Assistant | Envoyer et afficher un échange | Aucun double envoi ; reprise après erreur réseau |
| Mes échanges & projets | Lister et ouvrir les éléments autorisés | Isolation des données entre comptes |
| Laboratoire PDF | Importer, lister et récupérer un PDF privé | Taille/type contrôlés ; aucun lien public permanent |
| Compte / paramètres | Langue, session, déconnexion | Déconnexion effective et retour à l'accueil |
| Navigation | Retour visible et prévisible | Retour système et bouton interne sans perte de saisie non envoyée |

Le prototype ne doit afficher que les fonctions réellement accessibles via des services serveur testés. Ne pas présenter comme opérationnels les modules qui ne disposent pas encore d'un contrat API.

## 6. Contrats serveur à préparer

Pour chaque cas d'usage, documenter avant codage :
- méthode et chemin versionné (par exemple `/api/v1/conversations`) ;
- schéma JSON de requête/réponse et tailles maximales ;
- identité requise, droits et règles de propriété ;
- pagination, délais, limites de débit et stratégie de reprise ;
- codes d'erreur stables et identifiant de corrélation ;
- politique de journalisation et durée de conservation.

Ordre proposé : session/profil, liste et création de conversations, messages IA, registre de projets, liste/import/téléchargement PDF. Les opérations d'administration, paiements et fonctions sensibles ne font pas partie du premier incrément.

## 7. Plan de réalisation et portes de validation

### Sprint A — audit des services web
- Cartographier les fonctions Python existantes et leurs dépendances Streamlit.
- Identifier les fonctions réutilisables hors interface et les opérations qui exigent une API serveur.
- Vérifier les schémas Supabase, RLS, stockage privé et tests existants.
- Livrable : matrice fonction → service/API → table/stockage → autorisation → test.

### Sprint B — socle Android vide mais sécurisé
- Créer le projet Android, configuration des environnements, navigation et thème bleu nuit/cyan.
- Ajouter connexion native PKCE, gestion de session et déconnexion.
- Ne connecter aucune fonction métier tant que l'authentification n'est pas testée.
- Livrable : application de test installable sur appareil Android, sans secrets intégrés.

### Sprint C — parcours verticaux
- Ajouter un seul parcours à la fois : profil, conversation, projets, puis PDF.
- Tester erreurs réseau, reprise, clavier, rotation, tailles d'écran et accessibilité.
- Vérifier qu'un compte ne peut ni lire ni modifier les ressources d'un autre compte.
- Livrable : rapport de tests par parcours et démonstration sur appareil réel.

### Sprint D — préparation de distribution
- Générer un AAB signé pour piste de test interne uniquement.
- Vérifier la fiche de confidentialité, suppression de compte, politique de confidentialité, support et conformité Google Play.
- Ne soumettre au public qu'après validation explicite et revue des coûts/obligations.

## 8. Tests obligatoires avant pilote

- Connexion, annulation OAuth, retour depuis le navigateur, renouvellement et déconnexion.
- Compte A / compte B : aucune fuite de conversation, projet ou fichier.
- Réseau lent, hors ligne, reprise, serveur indisponible et limite de débit.
- Import PDF volumineux, type interdit, interruption, téléchargement et suppression.
- Retour Android, bouton Retour interne, clavier ouvert et saisie non envoyée.
- Appareil compact, tablette, thème système, tailles de police et lecteur d'écran.
- Analyse du paquet : absence de secrets, permissions minimales et dépendances à jour.

## 9. Hors périmètre du premier prototype

- Publication Google Play ou App Store.
- Paiements et abonnements natifs.
- Messagerie temps réel, notifications poussées et synchronisation hors ligne complète.
- Réécriture de l'application web ou migration de toutes les fonctions.
- Promesse de compatibilité iOS avant étude distincte.

## 10. Décision de passage

Le travail Android ne passe au pilote que lorsque l'authentification, les autorisations, les contrats API, l'isolation des données et les parcours principaux sont testés. La compilation d'un paquet ne vaut ni validation de sécurité ni publication sur un store.

**Règle de préservation :** le web Streamlit reste intact et fonctionnel pendant toute la réalisation mobile. Les changements de schéma ou d'API doivent être rétrocompatibles, migrés et testés avant leur activation.

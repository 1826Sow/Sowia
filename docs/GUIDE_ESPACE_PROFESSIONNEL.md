# Guide de l’espace Professionnel

Ce guide décrit les fonctions présentes dans l’application SOW IA. Il ne modifie ni l’application, ni les données, ni la configuration Supabase.

## 1. Choisir l’espace Professionnel

Dans la barre latérale, sélectionnez **Professionnel** dans le choix d’espace de travail. Le tableau de bord professionnel s’affiche sur la page **Accueil**.

Les espaces Personnel et Professionnel utilisent des contextes distincts. Vérifiez le nom de l’espace sélectionné avant de créer ou de consulter des éléments.

## 2. Comprendre le tableau de bord

Le tableau de bord présente trois indicateurs :

- **PDF enregistrés** : nombre de documents présents dans l’espace sélectionné, lorsque le stockage cloud est disponible.
- **Notes mémoire** : nombre de notes enregistrées dans la mémoire de cet espace.
- **Messages de cette session** : nombre de messages disponibles dans l’historique de la session courante.

Les raccourcis permettent d’ouvrir directement la création de PDF, les documents, la mémoire ou l’assistant.

Si le nombre de PDF ne peut pas être chargé, le tableau de bord l’indique sans modifier les fichiers.

## 3. Créer un document professionnel

1. Ouvrez **Créer un PDF**.
2. Dans la section **Modèles professionnels**, choisissez si besoin un modèle :
   - Courrier professionnel ;
   - Compte rendu de réunion ;
   - Proposition commerciale ;
   - Note interne.
3. Appuyez sur **Insérer le modèle**.
4. Modifiez librement le titre et le contenu.
5. Appuyez sur **Créer le PDF**, puis téléchargez le document.

La création du PDF à partir du texte saisi ne nécessite pas de crédit IA. Les modèles sont des points de départ éditables : relisez et adaptez toujours le document avant de l'envoyer.

## 4. Gérer les PDF privés

Dans **Mes documents**, lorsque le stockage cloud est configuré et accessible :

- ajoutez un fichier PDF de 10 Mo maximum ;
- recherchez un document par son nom ;
- triez la liste par nom ou par date d'ajout ;
- consultez la date d'ajout lorsqu'elle est disponible ;
- préparez le téléchargement d'un PDF ;
- lancez l'analyse d'un document enregistré ;
- demandez la confirmation avant une suppression définitive.

Le stockage est organisé par compte et par espace de travail. La disponibilité effective dépend de la configuration Supabase et de ses règles de sécurité. Ne déposez pas de documents sensibles tant que l'accès réel n'a pas été validé sur l'instance utilisée.

### Exporter sa mémoire

Dans **Ma mémoire**, utilisez **Télécharger ma mémoire (.txt)** pour enregistrer une copie des notes de l'espace actuellement sélectionné. L'export contient uniquement les notes visibles dans cet espace ; il n'inclut ni les conversations ni les documents PDF. Les espaces Personnel et Professionnel restent séparés.

## 5. Analyser un PDF

L'analyse d'un document enregistré nécessite un fournisseur IA configuré et disponible. En cas de quota ou de clé API indisponible, l'analyse peut échouer ; cela n'empêche pas les fonctions de création PDF qui n'utilisent pas l'IA.

Le texte extrait d'un PDF sélectionné est conservé dans la session pour l'analyse et n'est pas ajouté automatiquement à l'historique de conversation.

## 6. Bonnes pratiques

- Vérifiez toujours l'espace sélectionné avant toute opération.
- Utilisez des noms de fichiers explicites.
- Relisez les documents générés avant leur diffusion.
- Conservez une copie locale des documents importants.
- Ne partagez jamais vos clés API, vos secrets Supabase ou vos identifiants.
- Testez l'accès avec le compte concerné avant de considérer un document comme disponible en production.

## État des paiements

Le parcours PayPal Live a été autorisé et un test de paiement a été déclaré validé par le propriétaire. Cela ne suffit pas à confirmer que le parcours est actuellement opérationnel en production : la configuration des secrets côté hébergeur et serveur, la réception des webhooks et l'attribution effective des droits Premium doivent être vérifiées séparément.

Aucun paiement réel ne doit être effectué pour un simple contrôle technique. Ne considérez jamais un retour navigateur comme une preuve de paiement. Les secrets PayPal doivent rester dans les gestionnaires de secrets prévus et ne doivent jamais être ajoutés au dépôt GitHub.


### Contrôle de l'environnement SOWIA - TEST

Lors du contrôle du 21 novembre 2026, le projet Supabase de test ne présentait pas les fonctions Edge `paypal-one-time` et `paypal-webhook` dans la liste des fonctions déployées. Les migrations PayPal du dépôt n'apparaissaient pas non plus dans son historique de migrations. Le parcours PayPal ne doit donc pas être considéré comme déployé et vérifié sur cet environnement. Ce constat concerne uniquement le projet de test inspecté ; il ne permet pas de conclure sur un éventuel autre projet Supabase.

Avant toute activation sur un environnement cible, appliquer et vérifier les migrations requises, déployer les fonctions correspondantes, configurer les secrets côté Edge Function sans les exposer, puis vérifier le traitement des webhooks et l'attribution des droits Premium. Ne pas déployer partiellement la fonction ou activer les paiements si ces prérequis ne sont pas réunis.


Le contrôle en lecture seule du schéma `public` a également confirmé que, parmi les tables attendues par le parcours PayPal, seule `sowia_entitlements` existe dans le projet de test. Les tables `sowia_paypal_catalog`, `sowia_paypal_webhook_events`, `sowia_subscriptions` et `sowia_financial_transactions` n'y sont pas présentes. Il faut donc vérifier et appliquer la chaîne complète de migrations dans l'ordre prévu avant tout déploiement des fonctions ; appliquer uniquement les migrations additives de fin serait insuffisant.


Le workflow GitHub `.github/workflows/deploy-paypal-webhook.yml` cible explicitement le projet Supabase `qegcopordeqjiechmbhg` (projet `Sowia`, distinct de `SOWIA - TEST`) et exige une confirmation manuelle `DEPLOY`. Il ne doit pas être déclenché pendant la validation de test. Il ne déploie que `paypal-webhook`, pas `paypal-one-time`. La validation doit donc d'abord disposer d'un déploiement contrôlé sur le projet TEST et d'une procédure distincte pour chacune des deux fonctions ; aucune action de déploiement n'a été lancée.


Le webhook récurrent utilise aussi la table `sowia_paypal_subscription_blocks` pour gérer les blocages d'accès. Elle est également absente du schéma public du projet TEST inspecté. Cette table doit être incluse dans l'inventaire et la préparation des migrations avant tout test du webhook ; ne pas déployer la fonction seule en espérant que le schéma soit complet.

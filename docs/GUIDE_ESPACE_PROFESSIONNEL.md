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

### Configuration Supabase requise

Pour une nouvelle installation ou une mise à niveau du schéma, exécutez dans l'éditeur SQL Supabase, dans cet ordre :

1. `supabase/schema.sql` pour les tables, les colonnes d'espace de travail et les règles RLS des données.
2. `supabase/storage_security.sql` pour rendre le bucket `sowia-files` privé, limiter les fichiers aux PDF de 10 Mo et appliquer les règles de stockage par utilisateur.

Le second script est réexécutable : il remet le bucket dédié en mode privé et recrée les trois règles de lecture, d'envoi et de suppression. Après exécution, vérifiez le fonctionnement avec deux comptes de test distincts avant d'y déposer des documents réels. La présence de ces scripts dans GitHub ne signifie pas qu'ils ont déjà été exécutés sur le projet Supabase en production.

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

Les paiements restent désactivés pendant la finalisation de SOW IA. Ce guide ne demande aucune activation PayPal et ne modifie aucun réglage de paiement.

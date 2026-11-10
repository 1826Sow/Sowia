# SOWIA GLOBAL COLLABORATION HUB

## Objectif
Espace partagé pour organiser des projets entre entreprises, applications et partenaires SOWIA. Le module complète GLOBAL ID, DIRECTORY et CONNECT sans les remplacer.

## Fonctions de cette première version
- Création d'un projet avec objectif, pays/marché, date cible et indicateur de réussite.
- Invitations adressées à un profil GLOBAL ID public et publié, via son identifiant public SOWIA.
- Consentement explicite du destinataire : acceptation ou refus avant accès au projet.
- Rôles : propriétaire, coordinateur, contributeur et observateur.
- Contributions financières ou non financières (temps, expertise, technologie, réseau, autre).
- Jalons avec responsable, échéance et statut initial.
- Historique des créations, invitations, transitions, contributions et jalons.
- Transitions du projet réservées au propriétaire et enregistrées dans le journal.

## Sécurité et limites
- Les projets et leurs données sont visibles uniquement par le propriétaire et les membres ayant accepté l'invitation, selon RLS.
- Les invitations n'exposent pas les coordonnées privées.
- Les observateurs ne peuvent pas enregistrer de contributions ni créer de jalons.
- Les contributions financières sont des montants déclarés. Elles ne prouvent ni paiement, ni dépôt, ni transfert bancaire.
- Aucun contrat, paiement, achat, message externe ou prospection automatique n'est déclenché.
- Les changements de statut passent par une fonction RPC contrôlée et sont journalisés.
- Les contributions et jalons sont ajoutés sans écrasement de leur historique.

## Activation Supabase
Appliquer ce fichier dans Supabase SQL Editor après :
1. `supabase_global_id.sql`
2. `supabase_global_directory.sql`
3. `supabase_global_connect.sql`

Le fichier crée les tables, index, politiques RLS, fonctions RPC et déclencheurs d'audit. Il n'a pas été appliqué automatiquement à votre projet Supabase.

## Vérification
Les validations Python et les tests unitaires couvrent les champs de projet, les contributions, les jalons et les synthèses. Les tests RLS en conditions réelles nécessitent deux comptes Supabase de test configurés.

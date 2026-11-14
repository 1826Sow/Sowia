# Registre persistant « Mes échanges & projets »

## Ce que cette étape ajoute
- Une table `public.sowia_projects` par utilisateur et espace Personnel/Professionnel.
- Les statuts contrôlés : En cours, À tester, Validé, Terminé.
- Un rattachement facultatif à un identifiant de session de conversation.
- Un index de livrables (métadonnées/liens) et des métadonnées de reprise.
- Un archivage réversible par date, sans suppression des projets.

## Sécurité
La migration active RLS et limite lecture, création et modification à `auth.uid() = user_id`. Chaque fonction Python filtre également par propriétaire et espace. Les droits Premium ne sont pas modifiés par ce registre ; l'accès Professionnel continue d'être protégé par les contrôles déjà présents.

## Déploiement
Après fusion du changement applicatif, exécuter `supabase/migrations/20261114000100_sowia_project_register.sql` dans le SQL Editor Supabase. La migration est additive et ne modifie ni les messages ni les documents existants.

## Limites explicites
Ce registre fournit le stockage et les opérations CRUD sécurisées. Il ne prétend pas encore importer automatiquement toutes les anciennes sessions de chat ni découvrir les fichiers déjà stockés dans tous les modules. Le raccordement du Hub et l'indexation des conversations/livrables historiques restent nécessaires avant de présenter la liste comme exhaustive.

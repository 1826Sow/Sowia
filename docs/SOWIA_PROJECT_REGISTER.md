# Registre persistant « Mes échanges & projets »

## Ce que cette étape ajoute
- Une table `public.sowia_projects` par utilisateur et espace Personnel/Professionnel.
- Les statuts contrôlés : En cours, À tester, Validé, Terminé.
- Création, modification, archivage réversible et consultation des projets archivés.
- Un rattachement facultatif à un identifiant de session de conversation, avec raccourci de reprise.
- Un index de références de livrables (titre et lien HTTPS) et des métadonnées de reprise.
- Une entrée de navigation et un écran dédié dans le Hub SOW IA.

## Sécurité
La migration active RLS. Les opérations sont limitées à `auth.uid() = user_id`. Les lignes de l'espace Professionnel exigent également `public.sowia_has_professional_access()` dans les politiques SELECT, INSERT et UPDATE. Le contrôle d'accès Premium est donc appliqué au niveau de la base, et pas uniquement par masquage de l'interface. Chaque fonction Python filtre aussi par propriétaire et espace actif.

## Déploiement
Après revue et fusion du changement applicatif, exécuter `supabase/migrations/20261114000100_sowia_project_register.sql` dans le SQL Editor Supabase. Cette migration additive suppose que la fonction `public.sowia_has_professional_access()` déjà validée existe dans le projet. Elle ne modifie ni les messages ni les documents existants.

## Limites explicites
Les anciennes conversations ne sont pas importées automatiquement. La reprise fonctionne seulement lorsqu'un identifiant de session connu est associé au projet. L'index des livrables contient les références ajoutées manuellement dans le registre ; il ne constitue pas encore un inventaire automatique de tous les fichiers stockés dans les autres modules.

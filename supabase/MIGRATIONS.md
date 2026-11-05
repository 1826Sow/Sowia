# Migrations Supabase de la bibliothèque de documents

Ces scripts concernent le stockage cloud de la bibliothèque SOW IA. Ils ne sont pas exécutés automatiquement par l'application : un administrateur du projet Supabase doit les lancer dans **SQL Editor**.

## Installation neuve

Exécuter une seule fois, dans cet ordre :

1. `document_library.sql` — crée la table privée des documents, les colonnes de base, les index et les politiques RLS.
2. `document_trash_migration.sql` — ajoute `deleted_at`, nécessaire à la corbeille.
3. `comparison_history.sql` — crée l'historique privé des comparaisons, si cette fonction est utilisée.

Le script de création de la bibliothèque inclut déjà les colonnes `category` et `folder`.

## Projet Supabase déjà utilisé

Si la table `public.sowia_documents` existe déjà, exécuter les migrations manquantes dans cet ordre :

1. `document_category_migration.sql` — ajoute ou normalise la catégorie.
2. `document_folder_migration.sql` — ajoute ou normalise le dossier virtuel.
3. `document_trash_migration.sql` — ajoute la corbeille.
4. `comparison_history.sql` — uniquement si l'historique persistant des comparaisons n'est pas déjà installé.

Les migrations utilisent `IF NOT EXISTS` ou remplacent leurs contraintes/politiques nommées afin de pouvoir être rejouées dans les limites prévues par chaque script. Ne pas supprimer les politiques RLS et ne pas désactiver RLS pour contourner une erreur.

## Contrôle après exécution

Dans Supabase, vérifier que :

- `sowia_documents` contient `user_id`, `created_at`, `category`, `folder` et `deleted_at`.
- RLS est activé sur `sowia_documents`.
- Les politiques de lecture, insertion, modification et suppression restent limitées à `auth.uid() = user_id`.
- `sowia_comparison_history` existe avec RLS activé si l'historique persistant est utilisé.

Pour automatiser ce contrôle sans modifier la base, ouvrir `verify_security.sql` dans **SQL Editor** après les migrations. Ce script est strictement en lecture seule : il retourne une ligne par vérification, avec le statut `OK`, `À CORRIGER` ou `TABLE ABSENTE`. Les vérifications de l'historique de comparaison sont nécessaires si cette fonction est activée.

**Important :** ajouter `deleted_at` au schéma ne signifie pas que les migrations ont été exécutées sur le projet Supabase réel. L'application cloud ne doit être considérée comme prête pour la corbeille qu'après exécution et vérification de ces scripts sur le bon projet. Ne jamais publier une clé `service_role` dans Streamlit, le navigateur ou le dépôt GitHub.

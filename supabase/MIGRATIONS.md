# Migrations Supabase SOW IA

Ces scripts concernent le stockage cloud de la bibliothèque documentaire, de la mémoire privée et de l'historique. Ils ne sont pas exécutés automatiquement par l'application : un administrateur du projet Supabase doit les lancer dans **SQL Editor**.

## Installation neuve

Exécuter une seule fois, dans cet ordre :

1. `document_library.sql` — crée la table privée des documents, les colonnes de base, les index et les politiques RLS.
2. `document_trash_migration.sql` — ajoute `deleted_at`, nécessaire à la corbeille.
3. `comparison_history.sql` — crée l'historique privé des comparaisons.
4. `../supabase_schema.sql` (à la racine du dépôt) — crée les tables de mémoire privée (`sowia_memory_items`) et d'historique des conversations (`sowia_messages`), avec leurs index et politiques RLS.

## Projet Supabase déjà utilisé

Si la table `public.sowia_documents` existe déjà, exécuter uniquement les migrations qui manquent, dans cet ordre :

1. `document_category_migration.sql` — ajoute ou normalise la catégorie.
2. `document_folder_migration.sql` — ajoute ou normalise le dossier virtuel.
3. `document_trash_migration.sql` — ajoute la corbeille.
4. `comparison_history.sql` — uniquement si l'historique persistant des comparaisons n'est pas déjà installé.
5. `../supabase_schema.sql` — installer les tables de mémoire et de conversations si elles ne sont pas déjà présentes. Le script utilise `CREATE TABLE IF NOT EXISTS` et recrée les politiques nommées.

Ne pas supprimer les politiques RLS et ne pas désactiver RLS pour contourner une erreur. Vérifier le bon projet Supabase avant d'exécuter les scripts.

## Contrôle après exécution

Ouvrir `verify_security.sql` dans **SQL Editor** après les migrations. Le contrôle est strictement en lecture seule : il vérifie l'existence des quatre tables, les colonnes attendues, l'activation de RLS et les politiques d'accès limitées à `auth.uid() = user_id`. Il retourne une ligne par vérification avec le statut `OK`, `À CORRIGER` ou `TABLE ABSENTE`.

**Important :** la présence de scripts dans GitHub ne signifie pas que les migrations ont été exécutées sur le projet Supabase réel. La mémoire, les conversations, les documents et la corbeille ne doivent être considérés comme vérifiés en production qu'après exécution et contrôle sur le bon projet. Ne jamais publier une clé `service_role` dans Streamlit, le navigateur ou le dépôt GitHub.

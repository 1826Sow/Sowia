# FINAL TEC — proposition de cloisonnement des données investisseurs

**Statut : proposition technique non appliquée.** Le SQL associé est placé dans `supabase/proposals/`, hors du répertoire des migrations exécutables. Il ne doit pas être appliqué à la base de production sans inventaire préalable, environnement de test et validation humaine.

## Objectif

Créer un périmètre FINAL TEC indépendant des tables SOWIA existantes. Aucun changement n'est proposé aux tables de messages, mémoire, abonnements, paiements PayPal, transactions financières, incidents techniques ou fichiers privés SOWIA.

## Modèle proposé

### 1. `final_tec_investor_access`

Attribution nominative à un `auth.users.id`, limitée au projet `final-tec`, avec rôle, statut, dates de validité, auteur et motif d'attribution, et informations de révocation.

- Rôles prévus : `final_tec_admin`, `final_tec_analyst`, `final_tec_investor_viewer`.
- Le viewer n'obtient aucune permission d'écriture.
- Pas d'accès direct client à cette table ; gestion réservée au serveur.
- L'accès est refusé si l'attribution est absente, inactive, non commencée, expirée ou révoquée.

### 2. `final_tec_published_metrics`

Registre des indicateurs FINAL TEC avec valeur structurée, catégorie, unité, statut de preuve, source, horodatage, référence, responsable, hypothèses et horizon.

Les états de preuve sont distincts :
- `verified` : source HTTPS, date d'observation, référence de preuve et responsable obligatoires ;
- `projected` : hypothèses et horizon obligatoires ;
- `synthetic` : étiquette fictive obligatoire ;
- `pending` : non publiable.

La publication exige un approbateur et un horodatage. Les brouillons et éléments retirés ne sont pas visibles aux investisseurs.

### 3. `final_tec_investor_audit_log`

Journal dédié aux accès, refus et changements. Les clients ne peuvent ni le lire ni l'écrire. Le rôle serveur peut lire et ajouter des événements ; aucun droit client n'est accordé.

## Contrôle d'accès proposé

- RLS activée sur les trois tables.
- Le seul accès client prévu est un SELECT sur les indicateurs publiés.
- Une fonction SQL étroite vérifie côté serveur l'existence d'une attribution viewer active et non expirée.
- Aucune politique client n'est créée pour les attributions ou le journal.
- Aucune clé `service_role` ne doit être utilisée dans le navigateur ou exposée à Streamlit côté client.
- Les permissions d'administration et d'analyste devront être implémentées séparément côté serveur ; elles ne sont pas accordées par cette proposition SQL.

## Limites et points à résoudre avant test

1. Vérifier le schéma réel, les extensions disponibles, les migrations appliquées et les grants du projet Supabase cible.
2. Confirmer si les fonctions SQL SECURITY DEFINER existantes suivent une convention de sécurité particulière.
3. Ajouter les tests d'isolation avec deux utilisateurs distincts : viewer autorisé, viewer sans attribution, utilisateur révoqué, accès expiré et tentative de lecture croisée.
4. Ajouter un mécanisme serveur contrôlé pour créer/révoquer les attributions et publier/retirer les indicateurs.
5. Ajouter une journalisation serveur systématique, y compris des refus ; le SQL seul ne journalise pas automatiquement chaque requête refusée.
6. Définir les durées de conservation et les règles RGPD.
7. Faire relire les politiques par une personne compétente en sécurité Supabase/PostgreSQL.

## Critères de non-déploiement

Ne pas appliquer ce SQL à la production, ne pas créer d'invitations et ne pas ouvrir le tableau de bord à des investisseurs tant que les tests RLS réels, la révocation, les journaux, la provenance des données et la revue de sécurité ne sont pas validés.

**Cette proposition ne crée aucun accès réel, ne publie aucune donnée, ne contacte aucun investisseur et ne modifie aucune base Supabase.**

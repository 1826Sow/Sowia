# FINAL TEC — protocole de validation Supabase à deux identités

**Statut :** protocole préparatoire, non exécuté.  
**Portée :** environnement Supabase de test isolé uniquement.  
**Interdiction :** ne pas appliquer ce protocole à la production et ne pas ouvrir d'accès investisseur réel avant revue et autorisation distinctes.

## 1. Objectif et preuve attendue

Démontrer, sur un projet Supabase de test indépendant, que les contrôles FINAL TEC isolent correctement les données et appliquent le principe du moindre privilège.

La validation doit utiliser au minimum deux identités Auth distinctes :
- **Compte A — viewer autorisé :** affectation FINAL TEC active et non expirée, rôle strictement en lecture.
- **Compte B — utilisateur non autorisé :** aucune affectation FINAL TEC active.

Les tests doivent prouver les autorisations positives et les refus. Un test unitaire avec client simulé ou un PostgreSQL local avec imitation de `auth.role()` ne constitue pas cette preuve.

## 2. Conditions préalables — toutes obligatoires

- Projet Supabase de test dédié, sans données de production ni données personnelles réelles.
- Projet, région, URL et identifiant documentés dans le rapport de test (ne jamais publier de secret).
- Schéma SQL des PR #222 et #234 revu, versionné et approuvé avant toute application manuelle au projet de test.
- Fonctions RPC, politiques RLS et tables relues par une personne distincte de l'auteur si possible.
- Deux comptes Auth de test créés séparément ; leurs identifiants sont consignés sous forme de pseudonymes A/B dans le rapport.
- Secrets disponibles uniquement dans l'environnement CI sécurisé ou dans les secrets serveur du projet de test. Ne jamais les committer, les coller dans un ticket, ni les transmettre au navigateur.
- Le secret `service_role` reste strictement serveur ; les tests client utilisent les clés et jetons correspondant à leur identité.
- Nettoyage et procédure de remise à zéro du projet de test définis avant exécution.

Si une condition manque, le test est **bloqué**, pas réputé réussi.

## 3. Matrice de tests obligatoire

| ID | Identité / contexte | Action | Résultat attendu |
|---|---|---|---|
| AUTH-01 | A, viewer actif | Authentification | Session A reconnue côté serveur |
| AUTH-02 | B, sans affectation | Authentification | Session B reconnue, sans droit FINAL TEC |
| RLS-01 | anon | Lire les tables d'affectation et d'audit | Refus |
| RLS-02 | A | Lire directement les tables privées d'affectation et d'audit | Refus |
| RLS-03 | B | Lire les indicateurs publiés FINAL TEC | Aucune ligne accessible |
| RLS-04 | A | Lire les seuls indicateurs publiés autorisés | Lecture seule, lignes attendues uniquement |
| RPC-01 | A | Appeler le contrôle d'accès viewer | Autorisation positive stricte |
| RPC-02 | B | Appeler le contrôle d'accès viewer | Refus strict |
| RPC-03 | A ou B | Affectation expirée, révoquée ou rôle incompatible | Refus strict |
| WRITE-01 | A et B | Insérer/modifier/supprimer directement un indicateur publié | Refus |
| AUDIT-01 | Client A/B | Lire ou modifier le journal d'audit | Refus |
| AUDIT-02 | Serveur autorisé | Ajouter un événement via RPC contrôlée | Événement ajouté et chaîne cohérente |
| AUDIT-03 | Serveur | Modifier/supprimer un événement existant | Refus |
| APP-01 | B | Ouvrir FINAL TEC LIVE | Écran bloqué, aucun chiffre ni cache exposé |
| APP-02 | A | Ouvrir FINAL TEC LIVE avec registre vide | Message explicite, aucun chiffre fictif |
| APP-03 | A | Ouvrir FINAL TEC LIVE avec preuve publiée valide | Donnée, unité, source, date, statut et limites affichés |
| APP-04 | A | Simuler RPC indisponible ou réponse mal formée | Refus fermé, aucune donnée affichée |
| ISO-01 | A/B | Tenter d'accéder aux tables ou métriques SOWIA | Aucun accès indu ; aucune politique SOWIA modifiée |

## 4. Données de test

Utiliser uniquement des valeurs manifestement synthétiques et marquées `demo`, par exemple :
- une métrique publiée de test avec unité, fenêtre, source locale de test et protocole ;
- une métrique `pending_review` ;
- une projection avec horizon et hypothèses ;
- une preuve expirée ou révoquée.

Aucune de ces valeurs ne doit être présentée comme une performance réelle, une traction commerciale, un client, un revenu ou un benchmark FINAL TEC.

## 5. Procédure d'exécution

1. Vérifier que le projet cible est bien le projet de test isolé ; consigner son identifiant non secret.
2. Relire et faire approuver les fichiers SQL proposés ; vérifier qu'ils ne touchent aucune table ni politique SOWIA.
3. Appliquer manuellement les seules migrations approuvées au projet de test, après sauvegarde/export de son état initial.
4. Créer les comptes A et B ; établir l'affectation active de A et l'absence d'affectation de B.
5. Exécuter chaque test de la matrice séparément avec les jetons propres à l'identité testée.
6. Répéter les scénarios avec affectation expirée, révoquée et rôle incompatible.
7. Vérifier les journaux côté serveur et la chaîne d'audit ; ne pas exposer de jetons ni de données sensibles dans les logs.
8. Archiver les sorties, versions SQL, commit testé, date UTC, environnement, résultat et limites.
9. Détruire ou réinitialiser les données et comptes de test selon la procédure approuvée.

## 6. Critères de réussite

La validation est réussie uniquement si :
- tous les tests obligatoires ont été exécutés sur Supabase réel avec deux identités distinctes ;
- tous les refus attendus sont observés, et aucun accès indu n'est possible ;
- A ne peut lire que les données explicitement publiées et autorisées ;
- aucune écriture directe client n'est possible ;
- les erreurs d'authentification, de RPC ou de journalisation bloquent l'accès ;
- les événements d'audit sont traçables et non modifiables par les clients ;
- l'isolation avec SOWIA est démontrée ;
- les résultats et preuves sont relus par une personne distincte.

Un test ignoré, non configuré ou exécuté avec un faux client est noté **NON EXÉCUTÉ** et ne peut pas être compté comme succès.

## 7. Format du rapport de preuve

Pour chaque test : ID, date/heure UTC, commit, environnement (identifiant non secret), identité pseudonymisée A/B, préconditions, action, résultat attendu, résultat observé, statut PASS/FAIL/BLOCKED/NOT RUN, référence d'artefact et nom du vérificateur.

Ne jamais joindre de clé API, jeton JWT, secret service_role, adresse e-mail personnelle ou donnée de production.

## 8. Barrières de gouvernance

Ce protocole ne donne pas l'autorisation de :
- fusionner les PR #222 à #234 ;
- appliquer un SQL sur le projet Supabase de production ;
- ajouter un secret dans Streamlit ou GitHub ;
- inviter un investisseur ou activer un compte externe ;
- publier des métriques ou remplacer les données de démonstration ;
- modifier les données, paiements ou politiques de SOWIA.

Toute activation ultérieure nécessite une revue distincte, des preuves PASS archivées et une approbation explicite.

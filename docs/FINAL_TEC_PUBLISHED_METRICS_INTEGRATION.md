# FINAL TEC LIVE — branchement des indicateurs publiés

**Statut : proposition de code, non fusionnée et non déployée.** Cette étape prépare la lecture du registre Supabase ; elle ne connecte pas encore une base réelle.

## Fonctionnement

Après validation de l'autorisation viewer par le RPC de sécurité, l'application interroge uniquement `final_tec_published_metrics` avec les filtres `project_key = final-tec` et `publication_state = published`. La lecture reste soumise aux politiques RLS ; les filtres applicatifs ne remplacent pas RLS.

Le chargement est limité à 500 lignes et trié par date de publication décroissante.

## Contrôle de provenance avant affichage

Chaque ligne reçue est revérifiée côté application :
- `verified` : URL HTTPS, date d'observation, référence et responsable obligatoires ;
- `projected` : hypothèses et horizon obligatoires ;
- `synthetic` : étiquette explicite obligatoire ;
- `pending`, brouillons, lignes retirées ou enregistrements mal formés : exclus.

Le tableau affiche la nature de la donnée, la date de mesure, la date de publication, la référence, le responsable, la source et, le cas échéant, les hypothèses et l'horizon.

## Comportement en cas d'incident ou d'absence de données

- Source indisponible / exception / réponse invalide : message d'indisponibilité, aucun chiffre local de remplacement.
- Registre vide : message indiquant qu'aucun indicateur n'a été publié, tableau vide.
- Donnée invalide : ligne écartée, sans transformer son statut.
- Aucune série fictive n'est affichée dans la vue investisseur.

La fonction `build_demo_snapshot()` reste disponible pour les tests de maquette mais n'est plus appelée par le rendu de l'espace investisseur.

## Tests

Tests unitaires ajoutés pour :
- filtrage projet/publication ;
- rejet des brouillons, des statuts pending et des sources non HTTPS ;
- exigences des projections et données synthétiques ;
- source indisponible sans fallback fictif ;
- registre vide.

Le workflow ciblé exécute ces tests et compile les modules Python.

## Ce qui n'est pas encore validé

- Aucune base Supabase réelle n'a été interrogée dans cette tâche.
- Aucune migration de PR #222 n'a été appliquée.
- Les tests RLS à deux utilisateurs et la révocation en environnement Supabase de test restent à effectuer.
- Le SQL proposé doit être revu et testé avant toute application.
- Les indicateurs ne seront visibles qu'après publication explicite par un processus serveur autorisé.

**Aucun accès investisseur réel n'est créé et aucune donnée réelle n'est inventée ou publiée par cette modification.**

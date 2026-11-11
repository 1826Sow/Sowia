# FINAL TEC — EDGE ENGINE (simulation hors ligne)

**Statut : prototype de décision locale, non fusionné et non déployé.** Ce moteur classe uniquement une liste de ressources explicitement fournie et autorisée. Il ne contacte aucun fournisseur, ne réserve aucune capacité et ne lance aucune charge.

## Entrées
- Profil : type de charge, région, plafond p95, taux de succès minimal, budget maximal, devise/base de coût et fonctions matérielles requises.
- Candidats : identifiant, autorisation explicite, fonctions disponibles et benchmark associé.
- Instant de référence et fraîcheur maximale (24 h par défaut).

## Barrières impératives
Un candidat est exclu si l'autorisation manque, si le benchmark n'est pas à la fois `verified` et `published`, si charge/région ne correspondent pas, si les mesures sont absentes ou invalides/périmées, si devise/base de coût diffère, si une fonction manque, ou si les seuils de latence, disponibilité ou budget ne sont pas respectés. Les états `pending`, `draft`, `synthetic` et `projected` ne servent jamais de mesures de production.

## Classement explicable
Après les exclusions strictes, score pondéré configurable (défaut : latence 40 %, disponibilité 35 %, coût 25 %). Chaque résultat expose composantes, poids, identifiant et horodatage du benchmark. En cas d'égalité, l'identifiant de ressource assure un ordre déterministe. Les scores ne garantissent aucune performance.

## Sortie
Le moteur renvoie les candidats classés, les exclus et leurs motifs. Sans candidat admissible, il renvoie `no_eligible_resource` et ne choisit rien.

## Sécurité et limites
- Inventaire fourni manuellement ; aucune découverte automatique.
- Aucun appel réseau/API, runner distant, dispatch, provisionnement, écriture Supabase ou dépense.
- Aucun secret ni identifiant de connexion accepté.
- Le moteur suppose que `verified/published` provient du circuit serveur distinct ; il ne vérifie pas l'authenticité des mesures.
- `now` est fourni pour des tests reproductibles.
- Comparer uniquement des benchmarks réellement comparables.

Une exécution réelle exigerait une revue sécurité séparée, des ressources autorisées, des identités à privilèges minimaux, quotas, plafonds de dépenses, arrêt d'urgence, journalisation et approbation humaine. Rien de cela n'est activé par cette PR.

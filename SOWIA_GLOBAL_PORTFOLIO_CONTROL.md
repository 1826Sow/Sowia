# SOWIA GLOBAL PORTFOLIO CONTROL

Centre de revue des plans d'action par pays, échéance, plafond budgétaire, mesure de performance et alertes privées.

## Règles de contrôle
- Les plans affichés sont ceux créés par le compte connecté (le module de gouvernance peut aussi exposer les plans où le compte est approbateur).
- Une mesure utilise le dernier instantané par plan ; les cumuls historiques ne sont jamais additionnés.
- Les budgets sont ventilés par devise, sans conversion ni agrégation EUR/USD/etc.
- Les alertes actives, les échéances dépassées et les dépassements de plafond sont des signaux de revue séparés.
- Les évaluations de marché sont indicatives et déclaratives.
- Les statuts de revue sont explicables et ne constituent pas une notation globale du portefeuille.

## Sécurité et limites
Ce module est consultatif : il ne déplace pas d'argent, ne réaffecte pas les budgets, ne passe aucune commande, ne contacte aucun partenaire et ne modifie aucun plan. Toute décision de portefeuille reste humaine et doit passer par le processus d'approbation existant. Les données sont privées et limitées aux droits Supabase existants.

## Dépendances
Nécessite les migrations déjà prévues pour GLOBAL ACTION GOVERNANCE, GLOBAL PERFORMANCE & IMPACT, GLOBAL ALERTS et GLOBAL INTELLIGENCE. Ces migrations ne sont pas appliquées automatiquement par ce module.

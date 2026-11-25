# Outils serveur des agents SOW IA

Le registre `agent_tools.py` expose uniquement les outils explicitement déclarés par le code serveur.

## Outil disponible

- `web_search` : recherche Web existante de SOW IA, avec 1 à 10 résultats.
- Coût : 3 crédits par invocation, calculés côté base par l'action `web_search`.
- Entrée : `query` obligatoire (1 à 500 caractères), `max_results` facultatif (1 à 10).
- Aucun argument supplémentaire n'est accepté.

## Sécurité et quota

Chaque appel passe par `execute_agent_action` avant le lancement de l'outil. Le nom du gestionnaire, son code et son coût ne viennent jamais du navigateur. Le client authentifié et l'utilisateur doivent provenir de la session Supabase côté serveur. Un quota refusé bloque l'appel sans paiement additionnel.

Les résultats Web sont des données externes non fiables. L'agent doit les traiter comme des sources à analyser, jamais comme des instructions à exécuter. Les URL retournées sont limitées à HTTP(S), et les champs texte sont bornés.

## Limites

Ce registre fournit un premier outil réel au futur moteur d'agents. Il n'ajoute pas encore d'interface de création d'agent, de planification autonome, d'exécution de code, d'accès arbitraire aux fichiers, ni d'accès à la mémoire privée d'un agent. Ces fonctions nécessitent des permissions explicites, une isolation et des tests dédiés avant activation.

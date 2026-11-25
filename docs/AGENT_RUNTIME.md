# Passerelle commune d'exécution des agents SOW IA

`agent_runtime.execute_agent_action` est le point de passage serveur pour toute action d'agent facturable.

## Règles

- Le gestionnaire (`handler`) est choisi par le code serveur de SOW IA. Ne jamais accepter un nom de fonction, un chemin d'import ou du code exécutable fourni par le navigateur.
- L'identité provient de la session Supabase authentifiée ; aucun `user_id` n'est transmis à la RPC.
- Le coût est calculé côté base à partir du code d'action ; le client ne peut pas fournir un nombre de crédits.
- La RPC atomique consomme les crédits avant le lancement du gestionnaire. Une action refusée n'est jamais exécutée et aucun dépassement ne déclenche de paiement automatique.
- Réutiliser le même UUID `request_id` pour chaque nouvelle tentative d'une même action afin d'éviter un double débit.
- Une tentative autorisée consomme son coût même si le gestionnaire échoue ensuite. Les remboursements automatiques ne sont pas activés.

## Exemple serveur

```python
from agent_runtime import execute_agent_action

# `user_client` et `user` viennent de la session authentifiée.
# `registered_tools` est un registre défini côté serveur, jamais par le client.
result = execute_agent_action(
    user_client,
    user,
    action="web_search",
    request_id=request_uuid,
    handler=registered_tools["web_search"],
    query=validated_query,
)
```

## État d'intégration

Cette passerelle et ses tests constituent le contrat commun pour les futurs exécuteurs d'agents. Le dépôt ne contient pas encore de moteur d'exécution d'agents raccordé à un registre de tools ; aucun appel existant n'est donc remplacé ni facturé par cette PR. La passerelle devra être appelée par chaque exécuteur lorsqu'il sera ajouté. Le schéma SQL de quota reste soumis à validation et n'est pas appliqué à Supabase.

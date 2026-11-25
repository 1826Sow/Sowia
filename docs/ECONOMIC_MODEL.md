# Modèle économique SOW IA — première intégration

## Catalogue de lancement

- **Gratuit** : accès de base et quota de lancement de 1 000 crédits agent par mois et par compte.
- **Premium** : 9,90 € par mois pour l'accès professionnel existant. Le parcours d'abonnement mensuel déjà présent dans le dépôt reste distinct et n'est pas remplacé.
- **Agents IA** : chaque action consomme des crédits selon son poids. Les crédits sont partagés au niveau du compte; au-delà du quota, l'action est bloquée. Aucun dépassement payant automatique n'est autorisé.
- **Night Exchange** : commission calculable uniquement si un taux est explicitement approuvé. Aucun taux n'est activé par défaut.

## Barème indicatif de crédits

| Action | Crédits |
|---|---:|
| Conversation agent | 1 |
| Recherche Web | 3 |
| Génération de code | 5 |
| Analyse de fichier | 4 |
| Exécution d'outil | 2 |

Ces poids sont un barème initial de consommation, pas un prix en euros par action.

## Sécurité et limites de cette étape

- Le catalogue et les règles de calcul sont intégrés au code.
- Le module ne contacte aucun prestataire de paiement et ne débite aucun compte.
- Les compteurs mensuels persistants, la facturation des dépassements et les commissions réellement encaissées nécessitent une étape serveur dédiée et des migrations validées.
- Le taux Night Exchange et tout tarif de consommation supplémentaire restent à approuver.
- Les paiements réels restent désactivés par cette évolution.


## Compteur persistant des agents — préparation technique

Le service `agent_usage_quota.py` appelle deux RPC Supabase :
- `sowia_get_agent_usage` pour lire la consommation du mois UTC ;
- `sowia_consume_agent_credits` pour débiter atomiquement une action.

Le coût est recalculé côté PostgreSQL à partir du type d'action. Le client ne peut ni choisir son propre coût ni fournir l'identifiant d'un autre utilisateur. Chaque action exige un UUID de requête réutilisé en cas de retry, afin d'éviter les doubles débits. Les dépassements sont refusés sans achat automatique.

Le SQL est préparé dans `supabase/pending/agent_usage_quota_schema.sql`. **Ce fichier n'est pas une migration appliquée** : aucune modification n'a été faite sur le projet Supabase. Il devra être promu en migration via le CLI Supabase, relu, puis testé sur un environnement de développement avant toute application en production.

Les tables sont protégées par RLS et n'accordent aucun accès direct aux rôles clients. Les fonctions privilégiées sont explicitement retirées à `PUBLIC` et `anon`, accordées uniquement à `authenticated`, et utilisent `auth.uid()` pour déterminer le propriétaire. Le compteur s'affiche dans la rubrique Économie après installation des fonctions.


**Précision tarifaire :** le prix Premium de 9,90 € est mensuel, conformément au parcours d'abonnement PayPal déjà présent dans le dépôt. Il ne s'agit pas d'un achat unique.

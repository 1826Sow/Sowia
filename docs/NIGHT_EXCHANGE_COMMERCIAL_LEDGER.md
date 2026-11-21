# NIGHT EXCHANGE — registre commercial persistant

## Objectif métier

Construire un registre vérifiable des opérations NIGHT EXCHANGE afin de suivre :
- les propositions, échanges acceptés, opérations en cours, livrées, annulées et contestées ;
- les deux partenaires et leurs rôles dans chaque opération ;
- la valeur contractuelle, la devise, les frais et la commission SOW IA ;
- les montants effectivement encaissés, remboursés ou encore en attente ;
- l'activité des partenaires et les indicateurs agrégés par période et marché.

Le registre n'est pas un système de paiement autonome et ne doit jamais déclarer un revenu encaissé sur la seule base d'une offre acceptée ou d'une livraison déclarée.

## État du dépôt

- Une migration additive proposée crée les dossiers commerciaux et le journal d'événements append-only.
- Une seconde migration proposée ajoute une fonction de transition atomique avec contrôle du participant, verrouillage de ligne et clé d'idempotence.
- Une troisième migration proposée journalise automatiquement chaque création de proposition via un trigger interne, sans réutiliser la clé d'idempotence des transitions.
- Les migrations ne sont pas appliquées à Supabase ; aucune donnée ni configuration de production n'a été modifiée.
- Le prototype Streamlit comporte maintenant un onglet « Registre commercial » raccordé aux helpers Supabase : création d'une proposition via RPC, liste des contrats, transitions autorisées et consultation du journal.
- La persistance reste indisponible tant que les migrations nécessaires ne sont pas appliquées sur un projet Supabase de test. L'interface affiche alors un diagnostic et ne bascule pas sur un stockage local trompeur.
- L'interface Android n'est pas encore raccordée à ce registre.

## Cycle de vie des contrats

Transitions prévues dans la fonction serveur `sowia_nex_transition_deal` :

| État initial | État cible | Autorisation |
|---|---|---|
| proposed | accepted | contrepartie uniquement |
| proposed | cancelled | créateur uniquement |
| accepted | in_progress | l'un des deux participants |
| accepted | cancelled | l'un des deux participants |
| in_progress | completed | contrepartie uniquement |
| proposed / accepted / in_progress | disputed | l'un des deux participants |

Toute autre transition est rejetée. Une contestation ne peut pas être résolue par cette fonction ; la résolution exige une procédure de confiance distincte.

Chaque transition valide met à jour le statut et insère son événement `status_changed` dans la même transaction. Le verrou `FOR UPDATE` sérialise les transitions concurrentes sur un dossier. La clé d'idempotence, unique par acteur, permet de renvoyer l'événement initial lors d'une répétition sans rejouer la transition. Si la même clé est réutilisée avec un autre dossier, un autre état cible ou une autre note, la requête est rejetée.

## Journal et sécurité

- Les événements restent append-only ; aucune fonction cliente ne peut les modifier ou les supprimer.
- Chaque nouvelle proposition génère automatiquement un événement `proposal_created` dans le journal.
- La fonction utilise `SECURITY DEFINER` avec `search_path` vide, des noms d'objets qualifiés et vérifie `auth.uid()` ainsi que la participation au dossier.
- L'exécution est révoquée à `public` et `anon`, puis accordée uniquement à `authenticated`.
- La fonction ne peut pas confirmer un paiement, un remboursement ou une commission.
- Les droits directs du client sur les tables restent limités ; aucun secret `service_role` n'est placé dans l'application.

## Séparation financière

- Valeur contractuelle : montant convenu, sans présumer d'un encaissement.
- Commission prévue : calcul déterministe à partir du taux convenu.
- Paiement confirmé : uniquement après validation serveur du prestataire ou preuve comptable autorisée.
- Commission reconnue : uniquement selon une règle explicite après livraison et paiement confirmé, en tenant compte des remboursements et litiges.
- Échanges non monétaires : valeur déclarative séparée, jamais assimilée à du chiffre d'affaires encaissé.

## Dépendances et ordre de migration

1. Le registre d'applications NIGHT EXCHANGE existant doit être présent (`supabase_night_exchange_registry.sql`) afin de relier les contrats à des applications professionnelles approuvées.
2. Appliquer ensuite, sur un projet Supabase de test uniquement, les migrations `20261121000100`, `20261121000200`, `20261121000300` et `20261121000400` dans l'ordre.
3. Vérifier la création via RPC, les lectures RLS, les transitions, les refus d'accès, les répétitions d'idempotence et le journal automatique avant toute décision de déploiement.

## Tests et limites

Les tests statiques vérifient les invariants de la migration. Ils ne remplacent pas les tests PostgreSQL réels : rôles anon/authenticated/service_role, RLS, appels concurrents, répétitions d'idempotence, refus des transitions interdites et rollback transactionnel.

Aucune migration n'est appliquée en production. Aucun paiement, transfert, commission, publication publique ou approbation automatique n'est activé par cette étape. Les tests CI statiques et unitaires ne remplacent pas une validation PostgreSQL/RLS réelle.

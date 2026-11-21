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
- Une quatrième migration proposée ajoute la création de contrat par RPC : contrôle Premium serveur, deux applications approuvées, identité du partenaire dérivée depuis le registre et révocation de l'insertion directe cliente.
- Les quatre migrations ont été appliquées au projet isolé `SOWIA - TEST` (`mrbmoavotzcuzvnhfjla`) uniquement ; aucune migration ni donnée de production n'a été modifiée.
- Le prototype Streamlit comporte maintenant un onglet « Registre commercial » raccordé aux helpers Supabase : création de propositions via RPC, liste des contrats, transitions autorisées et consultation du journal.
- Vérification du projet de test : les deux tables, les deux RPC et le trigger d'audit sont présents ; RLS est activé sur les deux tables ; `authenticated` ne possède ni UPDATE ni DELETE direct, et ne peut plus insérer directement un contrat.
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

1. Le registre d'applications NIGHT EXCHANGE existant doit être présent (`supabase_night_exchange_registry.sql`) afin de relier les contrats à des applications professionnelles approuvées. La fonction d'accès Premium (`sowia_has_professional_access`) doit également être disponible.
2. Appliquer ensuite, sur un projet Supabase de test uniquement, les migrations `20261121000100`, `20261121000200`, `20261121000300` et `20261121000400` dans l'ordre.
3. Vérifier la création via RPC, les lectures RLS, les transitions, les refus d'accès, les répétitions d'idempotence et le journal automatique avant toute décision de déploiement.

## Tests et limites

Les tests CI Python/syntaxe sont réussis. Les quatre migrations ont été appliquées au projet isolé `SOWIA - TEST` et leur présence a été vérifiée par introspection PostgreSQL. Un contrôle sans session confirme que les deux RPC refusent les appels non authentifiés. Essais PostgreSQL transactionnels effectués dans `SOWIA - TEST` sous le rôle `authenticated`, en simulant les claims JWT de deux comptes professionnels Premium approuvés existants : création par le compte A, acceptation par le compte B, progression et clôture par le compte B ; événement de proposition automatique ; rejeu idempotent retournant le même événement ; transition interdite rejetée ; visibilité RLS pour les deux participants et invisibilité complète pour un tiers ; refus d'une transition par un non-participant ; rejet d'une clé de création réutilisée avec un contenu différent ; refus de l'insertion directe d'un contrat et de la modification directe du journal. Les transactions de test ont été annulées (`ROLLBACK`) : aucune donnée de test n'a été conservée. Ces essais SQL simulent les claims de session, mais ne remplacent pas encore un parcours HTTP avec deux sessions réellement connectées ni un test de concurrence multi-connexion.

Aucune migration n'est appliquée en production. Aucun paiement, transfert, commission, publication publique ou approbation automatique n'est activé par cette étape. Les contrôles Supabase signalent les RPC `SECURITY DEFINER` attendues et protégées par `auth.uid()` avec exécution réservée à `authenticated` ; ce point reste inclus dans la revue de sécurité avant déploiement.

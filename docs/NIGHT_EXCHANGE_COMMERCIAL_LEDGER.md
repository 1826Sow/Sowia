# NIGHT EXCHANGE — registre commercial persistant

## Objectif métier

Construire un registre vérifiable des opérations NIGHT EXCHANGE afin de suivre :
- les propositions, échanges acceptés, opérations en cours, livrées, annulées et contestées ;
- les deux partenaires et leurs rôles dans chaque opération ;
- la valeur contractuelle, la devise, les frais et la commission SOW IA ;
- les montants effectivement encaissés, remboursés ou encore en attente ;
- l'activité des partenaires et les indicateurs agrégés par période et marché.

Le registre n'est pas un système de paiement autonome et ne doit jamais déclarer un revenu encaissé sur la seule base d'une offre acceptée ou d'une livraison déclarée.

## Constat sur le dépôt au 21 novembre 2026

- Le prototype Streamlit NIGHT EXCHANGE sait présenter une fiche et une simulation de compatibilité, mais les brouillons et plafonds ne sont pas persistés.
- Les scripts SQL racine `supabase_night_exchange_registry.sql` et `supabase_night_exchange_events.sql` sont des propositions séparées, pas une migration versionnée dans `supabase/migrations/`.
- Le registre commercial append-only demandé n'est pas encore livré ni relié à l'interface.
- Le grand livre financier PayPal existant est distinct : il ne doit pas être détourné pour enregistrer des échanges non monétaires.
- La preuve DNS de domaine est préparée dans une PR indépendante ; elle ne vaut ni approbation juridique ni autorisation de paiement.

## Modèle de données cible

### 1. Dossier commercial

Chaque opération reçoit un identifiant stable et une clé d'idempotence. Elle référence les partenaires, leurs fiches d'application, l'espace de travail, le type d'opération, le périmètre convenu, la devise et les montants.

États métier proposés :
`proposed → accepted → in_progress → completed`
avec sorties contrôlées vers `cancelled` ou `disputed`. Une opération contestée ne doit pas être comptée comme livrée tant que le litige n'est pas résolu.

### 2. Journal d'événements immuable

Chaque changement important produit un événement horodaté : création, acceptation de chaque partie, démarrage, livraison, validation de livraison, contestation, résolution, confirmation de paiement ou remboursement. Les événements sont append-only ; les corrections passent par un nouvel événement, jamais par l'effacement de l'historique.

### 3. Séparation entre valeur et revenu reconnu

- Valeur contractuelle : montant convenu, sans présumer d'un encaissement.
- Commission prévue : calcul déterministe à partir d'un taux en points de base figé au moment de l'accord.
- Paiement confirmé : uniquement après validation côté serveur du prestataire ou preuve comptable autorisée.
- Commission reconnue : uniquement selon une règle explicite après livraison et paiement confirmé, en tenant compte des remboursements et litiges.
- Échanges non monétaires : valeur déclarative séparée, jamais assimilée à du chiffre d'affaires encaissé.

### 4. Indicateurs

Le tableau de bord pourra présenter le volume d'opérations par état, les échanges acceptés et terminés, la valeur contractuelle, les encaissements confirmés, les remboursements, les commissions reconnues, les partenaires actifs et les tendances par pays/période.

La part de marché ne sera jamais inventée à partir des seules données internes : elle nécessite un dénominateur externe documenté, daté et comparable.

## Exigences de sécurité

- Tables exposées en `public` protégées par RLS ; droits SQL et politiques RLS testés séparément.
- Les clients authentifiés ne peuvent ni créer ni modifier des écritures financières, ni insérer des événements de paiement.
- Écritures sensibles réservées au backend de confiance ; aucune clé `service_role` ou clé secrète dans Android, Streamlit client ou navigateur.
- Isolation par propriétaire, partenaire et espace de travail ; aucun accès transversal par simple connaissance d'un UUID.
- Idempotence sur les références externes et les webhooks.
- Montants en `numeric`, devises ISO 4217, taux de commission figé à l'accord.
- Aucun paiement, transfert, commission, publication publique ou approbation automatique activé par cette étape.

## Séquence de livraison

1. Revue du schéma existant et confirmation des migrations réellement appliquées en environnement de test.
2. Migration additive versionnée pour le dossier commercial et le journal immuable.
3. Tests SQL RLS allow/deny pour anon, authenticated et service_role, plus tests de transitions, idempotence, montants, remboursements et litiges.
4. Fonctions serveur typées pour enregistrer les événements et faire évoluer les états.
5. Lecture agrégée du registre dans le tableau de bord NIGHT EXCHANGE, sans modifier les fonctions existantes.
6. Revue sécurité et validation en environnement isolé avant toute proposition de déploiement Supabase.

## Hors périmètre de cette spécification

Cette branche ne modifie ni l'application, ni les secrets, ni les paramètres Supabase, ni les données de production, ni les paiements. Elle ne prétend pas livrer un registre opérationnel. La migration et l'intégration restent à réaliser et à vérifier avant activation.

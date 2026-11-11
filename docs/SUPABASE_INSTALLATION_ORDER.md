# SOW IA — ordre d’installation Supabase

Ce guide décrit l’ordre des scripts SQL réellement présents dans le dépôt. Il distingue le socle nécessaire, les modules facultatifs, les dépendances explicites et les scripts historiques ou liés aux paiements.

**Important :** le dépôt GitHub ne prouve pas quels scripts ont déjà été exécutés dans le projet Supabase. Avant toute exécution sur une base existante, sauvegarder la base et comparer le résultat de `supabase_full_diagnostics.sql`. Ne pas réexécuter une variante de schéma simplement parce qu’elle apparaît dans ce guide.

## 1. Socle de l’application

Pour une installation neuve du socle SOW IA, exécuter dans cet ordre :

1. `supabase/schema.sql` — tables privées de mémoire, messages et droits Premium.
2. `supabase_workspaces.sql` — ajoute la séparation Personnel / Professionnel aux messages et à la mémoire.
3. `supabase/migrations/20261111000200_sowia_professional_workspace_rls.sql` — applique le contrôle Premium au niveau RLS pour la mémoire et les messages. La vérification de l'abonnement récurrent est facultative et détectée seulement si `sowia_subscriptions` existe ; appliquer `supabase/migrations/20261109000100_sowia_subscriptions.sql` pour activer ce chemin.
4. `supabase/migrations/20261111000300_sowia_professional_modules_rls.sql` — ajoute le contrôle Premium aux tables CRM, calendrier relationnel, Business Club et NIGHT EXCHANGE. À exécuter après les scripts créant ces tables (CRM, calendrier, Business Club et NIGHT EXCHANGE), car ces tables doivent exister.
5. `supabase_storage_policies.sql` — bucket PDF privé et règles d’accès par utilisateur/espace ; ce script utilise la fonction créée à l'étape 3 pour protéger les dossiers `professional`.
4. `supabase_growth_crm.sql` — carnet de partenaires.
5. `supabase_language_preferences.sql` — préférences de langue par compte.
6. `supabase_business_opportunities.sql` — pipeline d’opportunités et prévisions commerciales.

Le script `supabase_accessibility_preferences.sql` est facultatif et doit être exécuté **après** `supabase_language_preferences.sql`, car il ajoute une colonne à `sowia_user_preferences`.

Ne pas confondre ce socle avec l’installation de tous les modules du dépôt : les modules ci-dessous sont facultatifs et ne doivent être installés que si la fonctionnalité correspondante est utilisée.

## 2. Modules facultatifs — ordre et dépendances

### CRM et Club Business

- `supabase_relationship_calendar.sql` — après `supabase_growth_crm.sql` (clé étrangère vers `sowia_growth_leads`).
- `supabase_business_club.sql` — base du Club Business.
- `supabase_business_club_notifications.sql` — après `supabase_business_club.sql`.

### Réseau d’impression et cartes VIP

1. `supabase_business_club.sql` doit déjà être installé.
2. `supabase_vip_printer_network.sql` — réseau de fournisseurs et devis ; dépend du Club Business.
3. Après le réseau d’impression, les deux scripts suivants peuvent être installés :
   - `supabase_vip_printer_reviews.sql`
   - `supabase_vip_card_orders.sql`

### SOWIA Night Exchange

1. `supabase_night_exchange_registry.sql` — registre des applications.
2. `supabase_night_exchange_events.sql` — événements ; dépend du registre.

### GLOBAL ID, annuaire et messagerie

Respecter cet ordre de dépendance :

1. `supabase_global_id.sql` — profils GLOBAL.
2. `supabase_global_directory.sql` — complète les profils créés à l’étape 1.
3. `supabase_global_connect.sql` — demandes de connexion ; dépend de GLOBAL ID.
4. `supabase_global_messenger.sql` — messagerie ; dépend des demandes de connexion.
5. `supabase_global_notifications.sql` — notifications ; dépend de la messagerie.
6. `supabase_global_trust.sql` — évaluations et signalements de confiance ; dépend des notifications et des connexions.
7. `supabase_global_moderation.sql` — modération ; dépend de GLOBAL Trust.
8. `supabase_global_intelligence.sql` — évaluations d’intelligence ; dépend de la modération.

### Autres modules GLOBAL

- `supabase_global_pulse.sql` — à installer avant `supabase_global_alerts.sql` (les alertes référencent les éléments Pulse).
- `supabase_global_alerts.sql` — dépend de GLOBAL Pulse.
- `supabase_global_decisions.sql` — analyses de décision.
- `supabase_global_learning.sql` — après `supabase_global_decisions.sql`.
- `supabase_global_action_governance.sql` — plans d’action et journal d’audit.
- `supabase_global_performance.sql` — après `supabase_global_action_governance.sql`.
- `supabase_global_forecast.sql` — prévisions stratégiques indépendantes.
- `supabase_global_collaboration.sql` — après **GLOBAL ID + GLOBAL DIRECTORY + GLOBAL CONNECT**.
- `supabase_global_collaboration_verify.sql` — diagnostic en lecture seule, après `supabase_global_collaboration.sql`. **Point à clarifier :** son en-tête parle de quatre migrations préalables, alors que le script d’installation GLOBAL Collaboration n’en nomme que trois (GLOBAL ID, DIRECTORY, CONNECT). Le quatrième prérequis n’étant pas nommé, ne pas considérer ce contrôle comme validé avant clarification.
- `supabase_decision_trials.sql` — essais comparatifs de décisions, indépendant des autres modules listés ici.
- `supabase_technology_candidates.sql` — évaluations technologiques, indépendant des autres modules listés ici.
- `supabase/migrations/20261110000200_sowia_technical_incidents.sql` — registre des incidents techniques, module opérationnel facultatif.

### Autres registres d’opportunités

Deux scripts créent des tables distinctes, avec des modèles de données différents :

- `supabase_opportunity_register.sql` crée `sowia_opportunities`.
- `supabase_opportunity_registry.sql` crée `sowia_opportunity_registry`.

Ils ne sont pas interchangeables et ne font pas partie du socle décrit dans le README. Ne pas installer les deux par défaut : vérifier d’abord quel module de l’application utilise quel schéma.

## 3. Finances et paiements — installation différée

Les scripts ci-dessous touchent aux droits Premium, au grand livre ou aux flux de paiement. Ils ne font pas partie du socle à installer automatiquement. Les paiements SOWIA restent désactivés tant que le propriétaire n’a pas validé explicitement leur mise en service.

- `supabase/migrations/20261110000100_sowia_financial_ledger.sql` — grand livre financier en lecture utilisateur ; migration distincte des flux de paiement.
- `supabase_paypal_refund_parent_migration.sql` — ancienne migration de liaison des remboursements. La migration actuelle du grand livre contient déjà le champ et le contrôle de remboursement correspondant ; ne pas appliquer cette ancienne migration en doublon sans audit.
- `supabase_entitlements_migration.sql` — évolution des droits Premium ; à planifier avec le schéma et le parcours d’abonnement.
- `supabase/migrations/20261109000100_sowia_subscriptions.sql` — table des abonnements.
- `supabase/migrations/20261109000200_sowia_paypal_catalog.sql` — catalogue PayPal.
- `supabase_crypto_payments.sql` — flux crypto et objets financiers associés ; **ne pas exécuter** dans le cadre de l’installation standard. Il touche également à `sowia_financial_transactions` et aux droits Premium : une revue dédiée de compatibilité est nécessaire avant toute utilisation.

Aucun de ces scripts ne suffit, à lui seul, à activer les paiements. Les secrets, webhooks, fonctions Edge, contrôles serveur, tests Sandbox et autorisation du propriétaire restent des étapes séparées.

## 4. Scripts de stockage et de finalisation

- `supabase_storage_policies.sql` est le script canonique de sécurisation du bucket PDF.
- `supabase/storage.sql` est marqué comme chemin de compatibilité historique. Ne pas l’exécuter en plus du script canonique dans une installation neuve.
- `supabase_storage_diagnostics.sql` est un diagnostic en lecture seule à lancer après le script canonique de stockage.
- `supabase/FINALISATION_SOWIA.sql` est un script consolidé historique qui reprend des éléments du schéma, du stockage et des abonnements. Ne pas le combiner avec l’installation modulaire ci-dessus : cela créerait des doublons de chemins d’installation.
- `supabase_full_diagnostics.sql` est le diagnostic général en lecture seule ; à lancer en dernier, après les seuls modules que l’on a choisi d’installer.

## 5. Ordre de contrôle conseillé

1. Sauvegarder la base Supabase.
2. Exécuter le diagnostic général et conserver son résultat.
3. Comparer les objets présents avec les modules réellement utilisés.
4. Installer uniquement le socle ou les modules nécessaires, en respectant leurs dépendances.
5. Exécuter les diagnostics ciblés (stockage ou GLOBAL Collaboration, si concernés).
6. Relancer `supabase_full_diagnostics.sql` et examiner chaque ligne `MISSING`, `RLS DISABLED`, `PUBLIC` ou colonne manquante.
7. Effectuer des tests d’isolation avec deux comptes distincts avant de déclarer la mise en production vérifiée.

Ce guide est une cartographie des scripts du dépôt, pas une preuve de leur exécution dans le projet Supabase. Les migrations de paiement restent volontairement séparées.

# Abonnements PayPal récurrents — SOW IA

Le parcours reste désactivé tant que `SOWIA_SUBSCRIPTIONS_ENABLED=false`.
Au premier clic de préparation, SOW IA crée automatiquement le produit et le forfait mensuel dans PayPal Sandbox, puis conserve les identifiants dans une table Supabase privée.

## Secrets Streamlit
- `SOWIA_SUBSCRIPTIONS_ENABLED=false` — conserver cette valeur jusqu'à validation complète
- `PAYPAL_CLIENT_ID`
- `PAYPAL_CLIENT_SECRET`
- `PAYPAL_MODE=sandbox`
- `PAYPAL_SUBSCRIPTION_RETURN_URL` — URL HTTPS publique de l'application SOW IA
- `PAYPAL_SUBSCRIPTION_CANCEL_URL` — URL HTTPS publique de l'application SOW IA
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY` — serveur uniquement, jamais dans le navigateur

Le tarif Sandbox prévu est **9,90 EUR par mois**. Il est défini côté serveur dans `paypal_subscriptions.py`.

## Migration et fonction Edge
Appliquer les migrations dans l'ordre chronologique du dépôt, en particulier les migrations nécessaires au parcours PayPal :
1. `supabase/migrations/20261109000100_sowia_subscriptions.sql` — état des abonnements et droits de lecture.
2. `supabase/migrations/20261109000200_sowia_paypal_catalog.sql` — catalogue privé des forfaits.
3. `supabase/migrations/20261110000100_sowia_financial_ledger.sql` — registre financier.
4. `supabase/migrations/20261111000100_paypal_billing_ledger_link.sql` — lien des échéances récurrentes.
5. `supabase/migrations/20261111000400_paypal_capture_order_link.sql` — lien des achats ponctuels aux commandes.
6. `supabase/migrations/20261111000500_paypal_subscription_atomic_reconciliation.sql` — réconciliation atomique, verrouillage concurrent et ordre chronologique des événements.

Déployer ensuite la fonction Edge `paypal-webhook`, puis configurer les secrets Edge : `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, `PAYPAL_SUBSCRIPTION_WEBHOOK_ID`, `PAYPAL_MODE=sandbox`.

Le secret `PAYPAL_PREMIUM_PLAN_ID` n'est plus nécessaire : le webhook lit le plan attendu depuis la table privée `sowia_paypal_catalog`.

Créer dans PayPal Sandbox le webhook pointant vers l'URL de la fonction Edge et sélectionner les événements gérés par le code :
   - Abonnements : `BILLING.SUBSCRIPTION.ACTIVATED`, `BILLING.SUBSCRIPTION.UPDATED`, `BILLING.SUBSCRIPTION.CANCELLED`, `BILLING.SUBSCRIPTION.SUSPENDED`, `BILLING.SUBSCRIPTION.EXPIRED`, `BILLING.SUBSCRIPTION.PAYMENT.FAILED`, `BILLING.SUBSCRIPTION.PAYMENT.SUCCEEDED`.
   - Paiements récurrents : `PAYMENT.SALE.COMPLETED`, `PAYMENT.SALE.REFUNDED`, `PAYMENT.SALE.REVERSED`.
   - Achats ponctuels (capture Orders API) : `PAYMENT.CAPTURE.REFUNDED`.
6. Conserver l'identifiant du webhook dans `PAYPAL_SUBSCRIPTION_WEBHOOK_ID`. Il doit correspondre exactement au webhook configuré pour cette URL et ce mode Sandbox.

Les événements de remboursement de capture ne sont pas interchangeables avec les événements `PAYMENT.SALE.*` des abonnements : les deux familles doivent être cochées.

## Sécurité et activation
- La création automatique du produit et du forfait est limitée à Sandbox.
- La table catalogue est privée, sans politique d'accès utilisateur; seul le service role peut la lire et l'écrire.
- Le webhook vérifie la signature PayPal puis relit l'abonnement auprès de PayPal.
- Un simple retour navigateur ne donne jamais accès à Premium.
- Garder `SOWIA_SUBSCRIPTIONS_ENABLED=false` jusqu'à application de la migration, déploiement Edge, configuration du webhook et tests Sandbox de bout en bout.
- Aucun paiement réel ne doit être activé sans décision séparée.

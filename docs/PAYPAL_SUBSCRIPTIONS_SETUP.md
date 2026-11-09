# PayPal recurring subscriptions — SOW IA

This implementation is isolated on the feature branch and is not active in production.

## Files
- `supabase/migrations/20261109000100_sowia_subscriptions.sql`: private subscription state table. Authenticated users may read only their own row; browser clients have no write policy.
- `supabase/functions/paypal-webhook/index.ts`: verifies PayPal webhook signatures, retrieves the current subscription from PayPal, validates its plan and SOW IA user UUID, then writes the reconciled state with the Supabase service role.

## Streamlit secrets for the gated checkout
The app's subscription button is hidden unless `SOWIA_SUBSCRIPTIONS_ENABLED=true` and the following Streamlit secrets are present:
- `SOWIA_SUBSCRIPTIONS_ENABLED=true` (keep false until backend Sandbox setup is complete)
- `PAYPAL_CLIENT_ID`
- `PAYPAL_CLIENT_SECRET`
- `PAYPAL_PREMIUM_PLAN_ID`
- `PAYPAL_MODE=sandbox`
- `PAYPAL_SUBSCRIPTION_RETURN_URL` (public HTTPS SOW IA app URL)
- `PAYPAL_SUBSCRIPTION_CANCEL_URL` (public HTTPS SOW IA app URL)

The PayPal webhook ID is not needed by the Streamlit checkout and must remain only in the Edge Function secrets.

## Required Supabase Edge Function secrets
Set these secrets for the `paypal-webhook` function:
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `PAYPAL_CLIENT_ID`
- `PAYPAL_CLIENT_SECRET`
- `PAYPAL_PREMIUM_PLAN_ID`
- `PAYPAL_SUBSCRIPTION_WEBHOOK_ID`
- `PAYPAL_MODE=sandbox` (keep sandbox until the full test is approved)

Never put the service-role key or PayPal secret in Streamlit UI, browser code, GitHub files, or public environment variables.

## PayPal webhook events
Subscribe the PayPal webhook to:
- `BILLING.SUBSCRIPTION.ACTIVATED`
- `BILLING.SUBSCRIPTION.UPDATED`
- `BILLING.SUBSCRIPTION.CANCELLED`
- `BILLING.SUBSCRIPTION.SUSPENDED`
- `BILLING.SUBSCRIPTION.EXPIRED`
- `BILLING.SUBSCRIPTION.PAYMENT.FAILED`
- `PAYMENT.SALE.COMPLETED`
- `PAYMENT.SALE.REFUNDED`
- `PAYMENT.SALE.REVERSED`

Do not register `PAYMENT.SALE.DENIED` for this handler: it is not currently processed. The handler reconciles failed-payment, refund, and reversal events against the subscription's current PayPal status before saving the subscription record.

## Activation order
1. Let the GitHub Actions workflow `PayPal subscription safety checks` run on this pull request; resolve any Python test, Deno formatting, or type-check failures.
2. Apply the SQL migration in Supabase.
3. Deploy the Edge Function and add its secrets.
4. Register its HTTPS URL as the webhook URL in PayPal Sandbox and copy the generated webhook ID into the Supabase secret.
5. Run end-to-end Sandbox tests for approval, renewal, failed payment, cancellation, suspension, and expiry.
6. The app contains a feature-flagged recurring checkout and reads active subscriptions through the user's RLS-scoped Supabase client. The checkout button is explicitly blocked whenever `PAYPAL_MODE` is not `sandbox`; keep the feature flag false until steps 2–5 are complete and verified.
7. Only after Sandbox end-to-end tests pass, separately approve any live-mode change.

The webhook is configured to accept PayPal callbacks without a Supabase JWT and verifies PayPal’s signature itself. It records reconciled subscription state in `sowia_subscriptions`. The app's Professional workspace and Abonnement page recognize either the existing one-time entitlement or an active recurring subscription through the user's RLS-scoped client. The checkout button remains hidden unless the recurring feature flag and required PayPal checkout settings are configured. A return from PayPal never grants access by itself; only the verified webhook can do so. The migration must be applied before recurring access can work; if the table is unavailable, the guard fails closed. Therefore this branch must not be treated as a complete subscription launch until Sandbox end-to-end tests pass.

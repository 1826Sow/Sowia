# PayPal recurring subscriptions — SOW IA

This implementation is isolated on the feature branch and is not active in production.

## Files
- `supabase/migrations/20261109000100_sowia_subscriptions.sql`: private subscription state table. Authenticated users may read only their own row; browser clients have no write policy.
- `supabase/functions/paypal-webhook/index.ts`: verifies PayPal webhook signatures, retrieves the current subscription from PayPal, validates its plan and SOW IA user UUID, then writes the reconciled state with the Supabase service role.

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
- `PAYMENT.SALE.COMPLETED`
- `PAYMENT.SALE.DENIED`
- `PAYMENT.SALE.REFUNDED`

## Activation order
1. Review and test this pull request.
2. Apply the SQL migration in Supabase.
3. Deploy the Edge Function and add its secrets.
4. Register its HTTPS URL as the webhook URL in PayPal Sandbox and copy the generated webhook ID into the Supabase secret.
5. Run end-to-end Sandbox tests for approval, renewal, failed payment, cancellation, suspension, and expiry.
6. Only after those pass, connect the app's Professional access guard to the new table and separately approve any live-mode change.

The webhook currently records reconciled subscription state only. It does not grant access by writing to `sowia_entitlements`, and the application access guard has not yet been changed. Therefore this branch must not be treated as a complete subscription launch.

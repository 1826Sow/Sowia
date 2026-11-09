# PayPal recurring subscriptions — webhook foundation

This is a server-side foundation only. It does not create a subscription checkout,
does not activate payments, and must not be treated as production-ready until
the deployment and Sandbox checklist below has passed.

## Safety defaults

- Keep Streamlit secret `SOWIA_PAYMENTS_ENABLED=false`.
- Do not place PayPal secrets in GitHub, Streamlit client code, or chat.
- Do not grant Premium from a browser return URL.
- Only the verified PayPal webhook may update the entitlement.
- The Personal workspace remains free.

## Deploy the Supabase Edge Function

From the repository root, after reviewing and applying the additive SQL migration
in the Supabase SQL Editor:

```sh
supabase functions deploy paypal-webhook --no-verify-jwt
```

The function is intentionally configured with `verify_jwt = false` because
PayPal cannot send a Supabase user JWT. It independently verifies the complete
webhook signature with PayPal before processing any event.

Set these Edge Function secrets in the Supabase project (never in Git):

- `PAYPAL_CLIENT_ID`
- `PAYPAL_CLIENT_SECRET`
- `PAYPAL_WEBHOOK_ID`
- `PAYPAL_MODE=sandbox` during tests; use `live` only after approval
- `PAYPAL_PREMIUM_PLAN_ID` (the exact active EUR plan ID)
- `PAYPAL_SUBSCRIPTION_RETURN_URL` (for example, the public SOW IA URL followed by `?paypal_subscription=return`)
- `PAYPAL_SUBSCRIPTION_CANCEL_URL` (the public SOW IA URL followed by `?paypal_subscription=cancel`)
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

## Configure PayPal Sandbox webhook

Webhook URL:

`https://<SUPABASE_PROJECT_REF>.supabase.co/functions/v1/paypal-webhook`

Subscribe to:
- `BILLING.SUBSCRIPTION.ACTIVATED`
- `BILLING.SUBSCRIPTION.UPDATED`
- `BILLING.SUBSCRIPTION.CANCELLED`
- `BILLING.SUBSCRIPTION.SUSPENDED`
- `BILLING.SUBSCRIPTION.EXPIRED`
- `PAYMENT.SALE.COMPLETED`
- `PAYMENT.SALE.REFUNDED`
- `PAYMENT.SALE.REVERSED`

Copy the webhook ID into the Supabase secret `PAYPAL_WEBHOOK_ID`.
The configured plan must have a fixed EUR price. In the Streamlit server secrets,
set `SOWIA_PAYMENTS_ENABLED=false` until all checks pass; when the Sandbox
flow is approved, configure the same switch only in the protected server
configuration, together with `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`,
`PAYPAL_PREMIUM_PLAN_ID`, `PAYPAL_MODE=sandbox`, and the two HTTPS return URLs.
The Abonnement page creates the subscription server-side and sends the buyer
to the returned PayPal approval link. Subscription creation must set
`custom_id` to the authenticated SOW IA user's UUID; the webhook rejects
events that do not resolve to a valid UUID and the configured plan.

## Important implementation boundary

The function fetches the subscription and plan directly from PayPal after
signature verification. It grants access only when PayPal reports the
subscription as `ACTIVE`, and marks a previously linked entitlement inactive
for non-active statuses. Event IDs are recorded for duplicate-delivery
protection.

The existing entitlement table requires a non-null `paypal_order_id`; until
a separately reviewed schema cleanup is made, the function stores a
namespaced `SUB-<subscription-id>` compatibility reference there.

This is not yet a complete billing product: checkout/subscription creation,
account-to-subscription binding UX, failed/refunded-payment policy, renewal
testing, observability, and production rollout still require implementation
and review. Keep payments disabled until all Sandbox cases are verified.

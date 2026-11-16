-- Align production financial tables with the existing PayPal application modules.
-- Additive only: preserve all existing entitlement and transaction rows.
begin;

alter table public.sowia_entitlements
  add column if not exists amount numeric(10,2),
  add column if not exists currency text;

alter table public.sowia_financial_transactions
  add column if not exists paypal_subscription_id text;

notify pgrst, 'reload schema';

commit;

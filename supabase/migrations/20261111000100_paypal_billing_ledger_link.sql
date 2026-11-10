-- Link each recurring PayPal billing event to its source subscription.
-- Additive and nullable so existing ledger rows remain unchanged.
begin;

alter table public.sowia_financial_transactions
    add column if not exists paypal_subscription_id text;

create index if not exists sowia_financial_transactions_paypal_subscription_idx
    on public.sowia_financial_transactions
       (user_id, paypal_subscription_id, occurred_at desc)
    where provider = 'paypal' and paypal_subscription_id is not null;

commit;

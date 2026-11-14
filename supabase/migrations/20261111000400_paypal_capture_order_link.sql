-- Preserve the PayPal order ID beside each one-time capture so verified
-- refunds can revoke the matching Premium entitlement without guessing.
begin;

alter table public.sowia_financial_transactions
    add column if not exists paypal_order_id text;

create index if not exists sowia_financial_transactions_paypal_order_idx
    on public.sowia_financial_transactions (user_id, paypal_order_id)
    where provider = 'paypal' and paypal_order_id is not null;

commit;

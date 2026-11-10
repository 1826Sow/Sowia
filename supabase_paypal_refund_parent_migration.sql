-- Add exact capture linkage for individual PayPal refunds.
-- Safe to run repeatedly. Existing refund rows remain unlinked and must stay
-- in manual review until reconciled from the provider.
begin;

alter table public.sowia_financial_transactions
    add column if not exists parent_capture_id text;

create index if not exists sowia_financial_transactions_parent_refunds_idx
    on public.sowia_financial_transactions
       (user_id, provider, parent_capture_id, transaction_type);

commit;

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


-- Enforce the refund ceiling atomically, including concurrent partial refunds.
-- Locking the parent payment row serializes all refund inserts for one capture.
create or replace function public.sowia_enforce_paypal_refund_capture_limit()
returns trigger
language plpgsql
set search_path = public, pg_temp
as $$
declare
    v_capture_gross numeric(30,12);
    v_prior_refunds numeric(30,12);
begin
    if new.provider <> 'paypal' or new.transaction_type <> 'refund' then
        return new;
    end if;

    if new.parent_capture_id is null or btrim(new.parent_capture_id) = '' then
        raise exception 'PayPal refund must reference its parent capture';
    end if;

    select gross_amount
      into v_capture_gross
      from public.sowia_financial_transactions
     where user_id = new.user_id
       and provider = 'paypal'
       and provider_payment_id = new.parent_capture_id
       and transaction_type = 'payment'
     for update;

    if not found then
        raise exception 'PayPal parent capture not found for this account';
    end if;

    select coalesce(sum(gross_amount), 0)
      into v_prior_refunds
      from public.sowia_financial_transactions
     where user_id = new.user_id
       and provider = 'paypal'
       and parent_capture_id = new.parent_capture_id
       and transaction_type = 'refund'
       and provider_payment_id <> new.provider_payment_id;

    if v_prior_refunds + new.gross_amount > v_capture_gross then
        raise exception 'Cumulative PayPal refunds exceed the parent capture amount';
    end if;

    return new;
end;
$$;

drop trigger if exists sowia_paypal_refund_capture_limit
    on public.sowia_financial_transactions;
create trigger sowia_paypal_refund_capture_limit
    before insert or update on public.sowia_financial_transactions
    for each row execute function public.sowia_enforce_paypal_refund_capture_limit();

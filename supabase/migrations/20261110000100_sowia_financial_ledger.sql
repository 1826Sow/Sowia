-- SOW IA financial ledger.
-- Additive migration: independent from crypto checkout and compatible with PayPal.
-- Client access is read-only and restricted to the authenticated owner.
begin;

create table if not exists public.sowia_financial_transactions (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    order_id uuid,
    provider text not null check (char_length(provider) between 1 and 40),
    provider_payment_id text not null,
    parent_capture_id text,
    transaction_type text not null
        check (transaction_type in ('payment', 'refund', 'fee_adjustment')),
    status text not null
        check (status in ('confirmed', 'refunded', 'reversed', 'manual_review')),
    gross_amount numeric(30,12) not null check (gross_amount >= 0),
    gross_currency text not null check (char_length(gross_currency) between 3 and 12),
    reference_amount_eur numeric(12,2),
    fee_amount numeric(30,12),
    fee_currency text,
    net_amount numeric(30,12),
    net_currency text,
    tax_amount_eur numeric(12,2),
    occurred_at timestamptz not null,
    created_at timestamptz not null default now(),
    unique (provider, provider_payment_id, transaction_type)
);

-- Bring forward installations where the ledger was created by the older
-- crypto-payments script, without replacing or deleting existing records.
alter table public.sowia_financial_transactions
    add column if not exists parent_capture_id text;

create index if not exists sowia_financial_transactions_user_date_idx
    on public.sowia_financial_transactions (user_id, occurred_at desc);

create index if not exists sowia_financial_transactions_parent_refunds_idx
    on public.sowia_financial_transactions
       (user_id, provider, parent_capture_id, transaction_type);

alter table public.sowia_financial_transactions enable row level security;

drop policy if exists "Users can read their own SOW IA financial transactions"
    on public.sowia_financial_transactions;

create policy "Users can read their own SOW IA financial transactions"
    on public.sowia_financial_transactions
    for select to authenticated
    using ((select auth.uid()) = user_id);

revoke all on public.sowia_financial_transactions from anon, authenticated;
grant select on public.sowia_financial_transactions to authenticated;

-- Prevent cumulative PayPal refunds from exceeding their parent capture.
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

commit;

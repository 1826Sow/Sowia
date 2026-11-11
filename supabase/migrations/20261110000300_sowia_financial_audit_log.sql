-- SOWIA immutable financial audit trail.
-- Additive migration: records successful ledger INSERT/UPDATE/DELETE operations.
-- The audit log contains only transaction metadata, never provider credentials.
begin;

create table if not exists public.sowia_financial_audit_log (
    event_id uuid primary key default gen_random_uuid(),
    ledger_row_id uuid,
    user_id uuid,
    actor_id uuid,
    actor_role text,
    operation text not null check (operation in ('INSERT', 'UPDATE', 'DELETE')),
    transaction_id bigint not null,
    changed_at timestamptz not null default clock_timestamp(),
    before_data jsonb,
    after_data jsonb
);

create index if not exists sowia_financial_audit_log_user_date_idx
    on public.sowia_financial_audit_log (user_id, changed_at desc);

create index if not exists sowia_financial_audit_log_row_date_idx
    on public.sowia_financial_audit_log (ledger_row_id, changed_at desc);

alter table public.sowia_financial_audit_log enable row level security;

-- The log is server-only. Authenticated clients cannot read or alter it.
revoke all on public.sowia_financial_audit_log from public, anon, authenticated, service_role;
grant select on public.sowia_financial_audit_log to service_role;

create or replace function public.sowia_prevent_financial_audit_mutation()
returns trigger
language plpgsql
set search_path = public, pg_temp
as $$
begin
    raise exception 'SOWIA financial audit records are immutable';
end;
$$;

drop trigger if exists sowia_financial_audit_immutable
    on public.sowia_financial_audit_log;

create trigger sowia_financial_audit_immutable
    before update or delete on public.sowia_financial_audit_log
    for each row execute function public.sowia_prevent_financial_audit_mutation();

create or replace function public.sowia_audit_financial_ledger_change()
returns trigger
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
    v_old jsonb;
    v_new jsonb;
    v_row jsonb;
begin
    if tg_op in ('UPDATE', 'DELETE') then
        v_old := jsonb_build_object(
            'id', old.id,
            'user_id', old.user_id,
            'order_id', old.order_id,
            'reference_amount_eur', old.reference_amount_eur,
            'tax_amount_eur', old.tax_amount_eur,
            'created_at', old.created_at,
            'provider', old.provider,
            'provider_payment_id', old.provider_payment_id,
            'parent_capture_id', old.parent_capture_id,
            'transaction_type', old.transaction_type,
            'status', old.status,
            'gross_amount', old.gross_amount,
            'gross_currency', old.gross_currency,
            'fee_amount', old.fee_amount,
            'fee_currency', old.fee_currency,
            'net_amount', old.net_amount,
            'net_currency', old.net_currency,
            'occurred_at', old.occurred_at
        );
    end if;

    if tg_op in ('INSERT', 'UPDATE') then
        v_new := jsonb_build_object(
            'id', new.id,
            'user_id', new.user_id,
            'order_id', new.order_id,
            'reference_amount_eur', new.reference_amount_eur,
            'tax_amount_eur', new.tax_amount_eur,
            'created_at', new.created_at,
            'provider', new.provider,
            'provider_payment_id', new.provider_payment_id,
            'parent_capture_id', new.parent_capture_id,
            'transaction_type', new.transaction_type,
            'status', new.status,
            'gross_amount', new.gross_amount,
            'gross_currency', new.gross_currency,
            'fee_amount', new.fee_amount,
            'fee_currency', new.fee_currency,
            'net_amount', new.net_amount,
            'net_currency', new.net_currency,
            'occurred_at', new.occurred_at
        );
    end if;

    v_row := coalesce(v_new, v_old);

    insert into public.sowia_financial_audit_log (
        ledger_row_id,
        user_id,
        actor_id,
        actor_role,
        operation,
        transaction_id,
        before_data,
        after_data
    ) values (
        (v_row ->> 'id')::uuid,
        (v_row ->> 'user_id')::uuid,
        auth.uid(),
        nullif(current_setting('request.jwt.claim.role', true), ''),
        tg_op,
        txid_current(),
        v_old,
        v_new
    );

    if tg_op = 'DELETE' then
        return old;
    end if;
    return new;
end;
$$;

drop trigger if exists sowia_financial_ledger_audit
    on public.sowia_financial_transactions;

create trigger sowia_financial_ledger_audit
    after insert or update or delete on public.sowia_financial_transactions
    for each row execute function public.sowia_audit_financial_ledger_change();

commit;

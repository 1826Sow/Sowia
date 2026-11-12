-- Atomically persist a validated one-time PayPal capture and its Premium entitlement.
-- A capture can grant access only on its first ledger insertion. Replays never
-- resurrect an old order over a newer entitlement or after a refund.
begin;

-- Keep the entitlement tier explicit and compatible with installations
-- whose legacy entitlement table predates the plan column.
alter table public.sowia_entitlements
    add column if not exists plan text;
update public.sowia_entitlements
   set plan = case when status = 'active' then 'premium' else 'free' end
 where plan is null;
alter table public.sowia_entitlements
    alter column plan set default 'free',
    alter column plan set not null;
do $plan_constraint$
begin
    if not exists (
        select 1 from pg_constraint
        where conrelid = 'public.sowia_entitlements'::regclass
          and conname = 'sowia_entitlements_plan_allowed'
    ) then
        alter table public.sowia_entitlements
            add constraint sowia_entitlements_plan_allowed
            check (plan in ('free', 'premium'));
    end if;
end
$plan_constraint$;

-- Make the RPC self-contained on installations that applied the base
-- entitlement schema but have not yet run the legacy additive SQL script.
alter table public.sowia_entitlements
    add column if not exists provider text;

alter table public.sowia_entitlements
    add column if not exists paypal_order_id text;

create unique index if not exists sowia_entitlements_paypal_order_id_uidx
    on public.sowia_entitlements (paypal_order_id)
    where paypal_order_id is not null;

create or replace function public.sowia_grant_paypal_one_time_entitlement(
    p_user_id uuid,
    p_order_id text,
    p_capture_id text,
    p_amount numeric,
    p_currency text
)
returns text
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_inserted_capture_id text;
    v_existing_user_id uuid;
    v_existing_order_id text;
    v_existing_amount numeric(30,12);
    v_existing_currency text;
    v_entitlement_order_id text;
    v_entitlement_status text;
begin
    if p_user_id is null
       or p_order_id is null
       or p_order_id !~ '^[A-Z0-9]{1,50}$'
       or p_capture_id is null
       or p_capture_id !~ '^[A-Z0-9_-]{5,100}$'
       or p_amount is null
       or p_amount <= 0
       or p_amount > 9999.99
       or p_amount <> round(p_amount, 2)
       or p_currency is distinct from 'EUR' then
        raise exception 'Invalid one-time PayPal entitlement input';
    end if;

    -- Serialize purchases for one user, including first-time inserts.
    perform pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended(p_user_id::text, 0)
    );

    -- A PayPal order is single-capture for this checkout. Do not allow a
    -- second capture ID to reuse an order already linked to this account.
    if exists (
        select 1
          from public.sowia_financial_transactions
         where user_id = p_user_id
           and provider = 'paypal'
           and paypal_order_id = p_order_id
           and transaction_type = 'payment'
           and provider_payment_id <> p_capture_id
    ) then
        raise exception 'PayPal order is already linked to another capture';
    end if;

    insert into public.sowia_financial_transactions (
        user_id, provider, provider_payment_id, paypal_order_id,
        transaction_type, status, gross_amount, gross_currency,
        reference_amount_eur, occurred_at
    ) values (
        p_user_id, 'paypal', p_capture_id, p_order_id,
        'payment', 'confirmed', p_amount, 'EUR', p_amount, pg_catalog.now()
    )
    on conflict (provider, provider_payment_id, transaction_type) do nothing
    returning provider_payment_id into v_inserted_capture_id;

    if v_inserted_capture_id is null then
        select user_id, paypal_order_id, gross_amount, gross_currency
          into v_existing_user_id, v_existing_order_id, v_existing_amount, v_existing_currency
          from public.sowia_financial_transactions
         where provider = 'paypal'
           and provider_payment_id = p_capture_id
           and transaction_type = 'payment'
         for update;

        if not found
           or v_existing_user_id <> p_user_id
           or v_existing_order_id is distinct from p_order_id
           or v_existing_amount <> p_amount
           or v_existing_currency <> 'EUR' then
            raise exception 'PayPal capture identity conflicts with existing ledger entry';
        end if;

        select paypal_order_id, status
          into v_entitlement_order_id, v_entitlement_status
          from public.sowia_entitlements
         where user_id = p_user_id
         for update;

        if v_entitlement_order_id = p_order_id and v_entitlement_status = 'active' then
            return 'already_granted';
        end if;

        -- A replayed capture must never replace a newer order or reactivate
        -- an entitlement revoked after a refund.
        return 'replay_ignored';
    end if;

    insert into public.sowia_entitlements (
        user_id, plan, status, provider, paypal_order_id, amount, currency, updated_at
    ) values (
        p_user_id, 'premium', 'active', 'paypal', p_order_id, p_amount, 'EUR', pg_catalog.now()
    )
    on conflict (user_id) do update
       set plan = excluded.plan,
           status = 'active',
           provider = 'paypal',
           paypal_order_id = excluded.paypal_order_id,
           amount = excluded.amount,
           currency = excluded.currency,
           updated_at = pg_catalog.now();

    return 'granted';
end;
$$;

revoke all on function public.sowia_grant_paypal_one_time_entitlement(uuid, text, text, numeric, text)
    from public, anon, authenticated;
grant execute on function public.sowia_grant_paypal_one_time_entitlement(uuid, text, text, numeric, text)
    to service_role;

commit;

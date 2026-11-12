-- Safe additive migration for existing SOW IA Premium entitlements.
-- Existing rows are preserved. Legacy rows remain NULL for the new metadata;
-- new PayPal grants populate both fields through premium_access.grant_paypal_entitlement.
begin;

-- Make the entitlement tier explicit on existing installations. Active legacy
-- PayPal grants become Premium; inactive rows remain Free.
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

alter table public.sowia_entitlements
    add column if not exists provider text;

alter table public.sowia_entitlements
    add column if not exists paypal_order_id text;

do $$
begin
    if not exists (
        select 1
        from pg_constraint
        where conname = 'sowia_entitlements_provider_check'
          and conrelid = 'public.sowia_entitlements'::regclass
    ) then
        alter table public.sowia_entitlements
            add constraint sowia_entitlements_provider_check
            check (provider is null or provider = 'paypal');
    end if;
end
$$;

create unique index if not exists sowia_entitlements_paypal_order_id_uidx
    on public.sowia_entitlements (paypal_order_id)
    where paypal_order_id is not null;

commit;

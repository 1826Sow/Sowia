-- Safe additive migration for existing SOW IA Premium entitlements.
-- Existing rows are preserved. Legacy rows remain NULL for the new metadata;
-- new PayPal grants populate both fields through premium_access.grant_paypal_entitlement.
begin;

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

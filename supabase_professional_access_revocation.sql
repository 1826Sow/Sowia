-- SOW IA: align Professional entitlement checks with PayPal revocations.
-- Additive and safe to re-run. Does not create or activate subscriptions.
begin;

alter table public.sowia_entitlements
    add column if not exists paypal_access_blocked boolean not null default false;

do $$
begin
    if pg_catalog.to_regclass('public.sowia_subscriptions') is not null then
        alter table public.sowia_subscriptions
            add column if not exists paypal_access_blocked boolean not null default false;
    end if;
end
$$;

create or replace function public.sowia_has_professional_access()
returns boolean
language plpgsql
stable
security definer
set search_path = ''
as $function$
declare
    current_user_id uuid;
    has_one_time_entitlement boolean := false;
    has_recurring_subscription boolean := false;
    subscriptions_table regclass;
begin
    current_user_id := (select auth.uid());
    if current_user_id is null then
        return false;
    end if;

    select exists (
        select 1
        from public.sowia_entitlements as entitlement
        where entitlement.user_id = current_user_id
          and entitlement.plan = 'premium'
          and entitlement.status = 'active'
          and entitlement.provider = 'paypal'
          and entitlement.paypal_access_blocked is false
    )
    into has_one_time_entitlement;

    subscriptions_table := pg_catalog.to_regclass('public.sowia_subscriptions');
    if subscriptions_table is not null then
        execute
            'select exists (
                select 1
                from public.sowia_subscriptions as subscription
                where subscription.user_id = $1
                  and subscription.provider = ''paypal''
                  and subscription.status = ''active''
                  and subscription.paypal_access_blocked is false
            )'
        into has_recurring_subscription
        using current_user_id;
    end if;

    return coalesce(
        has_one_time_entitlement or has_recurring_subscription,
        false
    );
end;
$function$;

revoke all on function public.sowia_has_professional_access() from public, anon;
grant execute on function public.sowia_has_professional_access() to authenticated, service_role;

commit;

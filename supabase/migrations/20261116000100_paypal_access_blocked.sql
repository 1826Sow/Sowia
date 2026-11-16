-- Add an explicit PayPal access-block flag to both Premium record types.
-- Existing records remain accessible by default; future refund/dispute workflows
-- can set the flag to TRUE. Application and SQL checks both fail closed on NULL.
begin;

alter table public.sowia_entitlements
    add column if not exists paypal_access_blocked boolean not null default false;

alter table public.sowia_subscriptions
    add column if not exists paypal_access_blocked boolean not null default false;

comment on column public.sowia_entitlements.paypal_access_blocked is
    'Server-managed PayPal refund/dispute access block. TRUE denies Professional access.';
comment on column public.sowia_subscriptions.paypal_access_blocked is
    'Server-managed PayPal refund/dispute access block. TRUE denies Professional access.';

-- Keep the database-level Professional access gate aligned with Python.
create or replace function public.sowia_has_professional_access()
returns boolean
language plpgsql
stable
security invoker
set search_path = ''
as $function$
declare
    current_user_id uuid;
    has_one_time_entitlement boolean := false;
    has_recurring_subscription boolean := false;
begin
    current_user_id := (select auth.uid());

    if current_user_id is null then
        return false;
    end if;

    if exists (
        select 1
        from pg_attribute
        where attrelid = 'public.sowia_entitlements'::regclass
          and attname = 'plan'
          and not attisdropped
    ) then
        execute
            'select exists (
                select 1
                from public.sowia_entitlements as entitlement
                where entitlement.user_id = $1
                  and entitlement.plan = ''premium''
                  and entitlement.status = ''active''
                  and entitlement.provider = ''paypal''
                  and entitlement.paypal_access_blocked is false
            )'
        into has_one_time_entitlement
        using current_user_id;
    else
        select exists (
            select 1
            from public.sowia_entitlements as entitlement
            where entitlement.user_id = current_user_id
              and entitlement.status = 'active'
              and entitlement.provider = 'paypal'
              and entitlement.paypal_access_blocked is false
        )
        into has_one_time_entitlement;
    end if;

    if to_regclass('public.sowia_subscriptions') is not null then
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

revoke all on function public.sowia_has_professional_access() from public;
revoke all on function public.sowia_has_professional_access() from anon;
grant execute on function public.sowia_has_professional_access() to authenticated;

commit;

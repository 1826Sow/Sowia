-- Enforce Professional workspace access in PostgreSQL itself.
-- The function is intentionally SECURITY INVOKER: the caller's JWT and the
-- users' own-row RLS policies remain in force while checking entitlement.
create or replace function public.sowia_has_professional_access()
returns boolean
language sql
stable
security invoker
set search_path = ''
as $function$
    select
        auth.uid() is not null
        and (
            exists (
                select 1
                from public.sowia_entitlements as entitlement
                where entitlement.user_id = auth.uid()
                  and entitlement.status = 'active'
            )
            or exists (
                select 1
                from public.sowia_subscriptions as subscription
                where subscription.user_id = auth.uid()
                  and subscription.provider = 'paypal'
                  and subscription.status = 'active'
            )
        );
$function$;

revoke all on function public.sowia_has_professional_access() from public;
revoke all on function public.sowia_has_professional_access() from anon;
grant execute on function public.sowia_has_professional_access() to authenticated;

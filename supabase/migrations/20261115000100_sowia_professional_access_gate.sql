-- Enforce Professional workspace access in PostgreSQL itself.
-- SECURITY INVOKER keeps the caller's JWT and owner-scoped RLS in force.
-- The recurring-subscription table is optional; one-time Premium entitlements
-- continue to work when that module has not been installed.

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

    select exists (
        select 1
        from public.sowia_entitlements as entitlement
        where entitlement.user_id = current_user_id
          and entitlement.plan = 'premium'
          and entitlement.status = 'active'
          and entitlement.provider = 'paypal'
    )
    into has_one_time_entitlement;

    -- The recurring module is optional. Use dynamic SQL only after confirming
    -- the table exists, so this migration also works without that module.
    if to_regclass('public.sowia_subscriptions') is not null then
        execute
            'select exists (
                select 1
                from public.sowia_subscriptions as subscription
                where subscription.user_id = $1
                  and subscription.provider = ''paypal''
                  and subscription.status = ''active''
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
grant select on public.sowia_entitlements to authenticated;
grant execute on function public.sowia_has_professional_access() to authenticated;

-- Grant recurring-subscription visibility only when the optional table exists.
-- Its own-row RLS policy must remain enabled.
do $grant_optional_subscription_read$
begin
    if to_regclass('public.sowia_subscriptions') is not null then
        execute 'grant select on public.sowia_subscriptions to authenticated';
    end if;
end;
$grant_optional_subscription_read$;

-- The workspace_id columns are added by supabase_workspaces.sql, which must
-- run before this migration. Replace owner-only policies with policies that
-- enforce ownership and Premium access for every Professional workspace row.

drop policy if exists "Users can read own messages" on public.sowia_messages;
create policy "Users can read own messages"
    on public.sowia_messages for select to authenticated
    using (
        (select auth.uid()) = user_id
        and (workspace_id = 'personal' or public.sowia_has_professional_access())
    );

drop policy if exists "Users can add own messages" on public.sowia_messages;
create policy "Users can add own messages"
    on public.sowia_messages for insert to authenticated
    with check (
        (select auth.uid()) = user_id
        and (workspace_id = 'personal' or public.sowia_has_professional_access())
    );

drop policy if exists "Users can delete own messages" on public.sowia_messages;
create policy "Users can delete own messages"
    on public.sowia_messages for delete to authenticated
    using (
        (select auth.uid()) = user_id
        and (workspace_id = 'personal' or public.sowia_has_professional_access())
    );

drop policy if exists "Users can read own memory" on public.sowia_memory_items;
create policy "Users can read own memory"
    on public.sowia_memory_items for select to authenticated
    using (
        (select auth.uid()) = user_id
        and (workspace_id = 'personal' or public.sowia_has_professional_access())
    );

drop policy if exists "Users can add own memory" on public.sowia_memory_items;
create policy "Users can add own memory"
    on public.sowia_memory_items for insert to authenticated
    with check (
        (select auth.uid()) = user_id
        and (workspace_id = 'personal' or public.sowia_has_professional_access())
    );

drop policy if exists "Users can delete own memory" on public.sowia_memory_items;
create policy "Users can delete own memory"
    on public.sowia_memory_items for delete to authenticated
    using (
        (select auth.uid()) = user_id
        and (workspace_id = 'personal' or public.sowia_has_professional_access())
    );

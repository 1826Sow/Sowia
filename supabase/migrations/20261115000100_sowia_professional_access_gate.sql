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
grant select on public.sowia_subscriptions to authenticated;
grant execute on function public.sowia_has_professional_access() to authenticated;

-- The workspace_id columns are added by supabase_workspaces.sql, which must
-- run before this migration. Replace the owner-only policies with policies
-- that also enforce the Premium gate for every Professional workspace row.

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

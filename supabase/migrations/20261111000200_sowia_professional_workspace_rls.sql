-- Enforce Premium entitlement at the database boundary for Professional workspace rows.
-- Additive and safe to re-run. Existing rows and Personal access are preserved.
begin;

-- Make the migration independent of the legacy manual workspace upgrade file.
alter table public.sowia_memory_items
    add column if not exists workspace_id text not null default 'personal';
alter table public.sowia_messages
    add column if not exists workspace_id text not null default 'personal';

do $constraints$
begin
    if not exists (
        select 1 from pg_constraint
        where conrelid = 'public.sowia_memory_items'::regclass
          and conname = 'sowia_memory_items_workspace_id_check'
    ) then
        alter table public.sowia_memory_items
            add constraint sowia_memory_items_workspace_id_check
            check (workspace_id in ('personal', 'professional'));
    end if;
    if not exists (
        select 1 from pg_constraint
        where conrelid = 'public.sowia_messages'::regclass
          and conname = 'sowia_messages_workspace_id_check'
    ) then
        alter table public.sowia_messages
            add constraint sowia_messages_workspace_id_check
            check (workspace_id in ('personal', 'professional'));
    end if;
end
$constraints$;

create or replace function public.sowia_has_professional_access()
returns boolean
language sql
stable
security definer
set search_path = ''
as $function$
    select
        (select auth.uid()) is not null
        and (
            exists (
                select 1
                from public.sowia_entitlements as entitlement
                where entitlement.user_id = (select auth.uid())
                  and entitlement.status = 'active'
                  and entitlement.provider = 'paypal'
            )
            or exists (
                select 1
                from public.sowia_subscriptions as subscription
                where subscription.user_id = (select auth.uid())
                  and subscription.status = 'active'
                  and subscription.provider = 'paypal'
            )
        );
$function$;

revoke all on function public.sowia_has_professional_access() from public, anon;
grant execute on function public.sowia_has_professional_access() to authenticated;

-- Restrictive policies are ANDed with the existing owner-only policies.
-- They add the Premium check without replacing or weakening user ownership.
drop policy if exists "Require Premium for Professional memories"
    on public.sowia_memory_items;
create policy "Require Premium for Professional memories"
    on public.sowia_memory_items
    as restrictive
    for all
    to authenticated
    using (
        workspace_id = 'personal'
        or public.sowia_has_professional_access()
    )
    with check (
        workspace_id = 'personal'
        or public.sowia_has_professional_access()
    );

drop policy if exists "Require Premium for Professional messages"
    on public.sowia_messages;
create policy "Require Premium for Professional messages"
    on public.sowia_messages
    as restrictive
    for all
    to authenticated
    using (
        workspace_id = 'personal'
        or public.sowia_has_professional_access()
    )
    with check (
        workspace_id = 'personal'
        or public.sowia_has_professional_access()
    );

commit;

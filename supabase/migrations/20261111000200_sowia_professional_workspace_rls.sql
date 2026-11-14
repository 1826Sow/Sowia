-- Enforce Premium entitlement at the database boundary for Professional workspace rows.
-- Additive and safe to re-run. Existing rows and Personal access are preserved.
begin;

-- Make the migration independent of the legacy manual workspace upgrade file.
-- Normalize the entitlement tier before using it as a database authorization condition.
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
language plpgsql
stable
security definer
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
    ) into has_one_time_entitlement;

    -- Recurring subscriptions are an optional module. Use a fixed, trusted
    -- query only when its table has been installed; otherwise fail closed
    -- for recurring access while preserving one-time entitlements.
    if to_regclass('public.sowia_subscriptions') is not null then
        execute
            'select exists (
                select 1
                from public.sowia_subscriptions as subscription
                where subscription.user_id = $1
                  and subscription.status = ''active''
                  and subscription.provider = ''paypal''
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

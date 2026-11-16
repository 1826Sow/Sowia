begin;

-- Remove legacy permissive gates that checked Premium status without checking
-- row ownership. PostgreSQL combines permissive policies with OR, so these
-- policies could otherwise expose another Premium user's Professional rows.
drop policy if exists "Require Premium for Professional messages" on public.sowia_messages;
drop policy if exists "Require Premium for Professional memories" on public.sowia_memory_items;

-- Remove both repository-era and deployed-database policy names so this
-- migration safely reconciles schema drift without changing any stored data.
drop policy if exists "Users can read own messages" on public.sowia_messages;
drop policy if exists "Users can add own messages" on public.sowia_messages;
drop policy if exists "Users can delete own messages" on public.sowia_messages;
drop policy if exists "Users can update own messages" on public.sowia_messages;
drop policy if exists messages_select_own on public.sowia_messages;
drop policy if exists messages_insert_own on public.sowia_messages;
drop policy if exists messages_delete_own on public.sowia_messages;
drop policy if exists messages_update_own on public.sowia_messages;

drop policy if exists "Users can read own memory" on public.sowia_memory_items;
drop policy if exists "Users can add own memory" on public.sowia_memory_items;
drop policy if exists "Users can delete own memory" on public.sowia_memory_items;
drop policy if exists "Users can update own memory" on public.sowia_memory_items;
drop policy if exists memory_select_own on public.sowia_memory_items;
drop policy if exists memory_insert_own on public.sowia_memory_items;
drop policy if exists memory_delete_own on public.sowia_memory_items;
drop policy if exists memory_update_own on public.sowia_memory_items;

-- Every operation now enforces both row ownership and workspace entitlement.
-- Personal rows remain available to their owner; Professional rows additionally
-- require the authenticated owner to hold Premium access.
create policy messages_select_own
on public.sowia_messages for select to authenticated
using (
  (select auth.uid()) = user_id
  and (workspace_id = 'personal' or (select public.sowia_has_professional_access()))
);

create policy messages_insert_own
on public.sowia_messages for insert to authenticated
with check (
  (select auth.uid()) = user_id
  and (workspace_id = 'personal' or (select public.sowia_has_professional_access()))
);

create policy messages_update_own
on public.sowia_messages for update to authenticated
using (
  (select auth.uid()) = user_id
  and (workspace_id = 'personal' or (select public.sowia_has_professional_access()))
)
with check (
  (select auth.uid()) = user_id
  and (workspace_id = 'personal' or (select public.sowia_has_professional_access()))
);

create policy messages_delete_own
on public.sowia_messages for delete to authenticated
using (
  (select auth.uid()) = user_id
  and (workspace_id = 'personal' or (select public.sowia_has_professional_access()))
);

create policy memory_select_own
on public.sowia_memory_items for select to authenticated
using (
  (select auth.uid()) = user_id
  and (workspace_id = 'personal' or (select public.sowia_has_professional_access()))
);

create policy memory_insert_own
on public.sowia_memory_items for insert to authenticated
with check (
  (select auth.uid()) = user_id
  and (workspace_id = 'personal' or (select public.sowia_has_professional_access()))
);

create policy memory_update_own
on public.sowia_memory_items for update to authenticated
using (
  (select auth.uid()) = user_id
  and (workspace_id = 'personal' or (select public.sowia_has_professional_access()))
)
with check (
  (select auth.uid()) = user_id
  and (workspace_id = 'personal' or (select public.sowia_has_professional_access()))
);

create policy memory_delete_own
on public.sowia_memory_items for delete to authenticated
using (
  (select auth.uid()) = user_id
  and (workspace_id = 'personal' or (select public.sowia_has_professional_access()))
);

commit;

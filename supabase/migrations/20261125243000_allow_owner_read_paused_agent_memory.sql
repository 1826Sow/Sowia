-- Owners must retain access to their own private agent memories when an agent is paused or archived,
-- so they can review and delete those memories. This does not grant other users access.
begin;

drop policy if exists sowia_agent_memory_select_own on public.sowia_agent_memory_items;
create policy sowia_agent_memory_select_own on public.sowia_agent_memory_items
    for select to authenticated
    using (
        user_id = (select auth.uid())
        and (workspace_id = 'personal' or public.sowia_has_professional_access())
        and exists (
            select 1 from public.sowia_agents a
            where a.id = sowia_agent_memory_items.agent_id
              and a.user_id = (select auth.uid())
              and a.workspace_id = sowia_agent_memory_items.workspace_id
        )
    );

commit;

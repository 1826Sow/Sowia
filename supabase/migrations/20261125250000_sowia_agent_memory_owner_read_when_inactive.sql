-- Owners must retain read access to their own private agent memories
-- so they can inspect and delete them after pausing or archiving an agent.
-- This does not grant insert/update access or expose another owner's rows.

begin;

drop policy if exists sowia_agent_memory_select_own
    on public.sowia_agent_memory_items;

create policy sowia_agent_memory_select_own
    on public.sowia_agent_memory_items
    for select to authenticated
    using (
        user_id = (select auth.uid())
        and (
            workspace_id = 'personal'
            or public.sowia_has_professional_access()
        )
    );

commit;

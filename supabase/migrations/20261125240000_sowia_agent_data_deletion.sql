-- Allow an authenticated owner to delete exactly one agent conversation.
-- Message rows are removed by the conversation FK ON DELETE CASCADE.
begin;

create or replace function public.sowia_delete_my_agent_conversation(
    p_agent_id uuid,
    p_conversation_id uuid,
    p_workspace_id text
)
returns boolean
language plpgsql
security definer
set search_path = pg_catalog
as $function$
declare
    v_user_id uuid := auth.uid();
    v_deleted integer;
begin
    if v_user_id is null then
        raise exception 'Authentication required.' using errcode = '42501';
    end if;

    if p_agent_id is null or p_conversation_id is null then
        raise exception 'Invalid agent or conversation identifier.' using errcode = '22023';
    end if;

    if p_workspace_id not in ('personal', 'professional') then
        raise exception 'Invalid workspace.' using errcode = '22023';
    end if;

    if p_workspace_id = 'professional'
       and not public.sowia_has_professional_access() then
        raise exception 'Professional access required.' using errcode = '42501';
    end if;

    delete from public.sowia_agent_conversations c
    where c.id = p_conversation_id
      and c.agent_id = p_agent_id
      and c.user_id = v_user_id
      and c.workspace_id = p_workspace_id;

    get diagnostics v_deleted = row_count;
    return v_deleted = 1;
end;
$function$;

revoke all on function public.sowia_delete_my_agent_conversation(uuid, uuid, text)
from public, anon, authenticated;
grant execute on function public.sowia_delete_my_agent_conversation(uuid, uuid, text)
to authenticated;

commit;

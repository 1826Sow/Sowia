-- User-requested deletion of one complete SOW IA conversation.
-- Only the authenticated owner and selected workspace/session can be affected.
begin;

create or replace function public.sowia_delete_my_conversation(
    p_session_id text,
    p_workspace_id text
)
returns boolean
language plpgsql
security definer
set search_path = pg_catalog
as $function$
declare
    v_user_id uuid := auth.uid();
    v_registry_found boolean;
begin
    if v_user_id is null then
        raise exception 'Authentication required.' using errcode = '42501';
    end if;

    if p_session_id is null
       or char_length(p_session_id) < 1
       or char_length(p_session_id) > 128 then
        raise exception 'Invalid conversation identifier.' using errcode = '22023';
    end if;

    if p_workspace_id not in ('personal', 'professional') then
        raise exception 'Invalid workspace.' using errcode = '22023';
    end if;

    if p_workspace_id = 'professional'
       and not public.sowia_has_professional_access() then
        raise exception 'Professional access required.' using errcode = '42501';
    end if;

    select exists (
        select 1
        from public.sowia_conversations c
        where c.user_id = v_user_id
          and c.workspace_id = p_workspace_id
          and c.session_id = p_session_id
    ) into v_registry_found;

    if not v_registry_found then
        return false;
    end if;

    delete from public.sowia_messages m
    where m.user_id = v_user_id
      and m.workspace_id = p_workspace_id
      and m.session_id = p_session_id;

    delete from public.sowia_conversations c
    where c.user_id = v_user_id
      and c.workspace_id = p_workspace_id
      and c.session_id = p_session_id;

    return true;
end;
$function$;

revoke all on function public.sowia_delete_my_conversation(text, text)
from public, anon, authenticated;
grant execute on function public.sowia_delete_my_conversation(text, text)
to authenticated;

commit;
